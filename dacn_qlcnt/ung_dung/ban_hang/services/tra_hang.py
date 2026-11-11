"""Trả hàng: khách gửi yêu cầu cho đơn đã hoàn thành, quản lý chi nhánh duyệt và hoàn tiền.

Thuốc đã bán chỉ nhận trả khi lỗi thuộc nhà thuốc (giao sai, hư hỏng, hết hạn). Khi duyệt,
quản lý đã nhận lại hàng, chọn đúng lô của từng hộp trong các lô đã xuất cho đơn:
- hàng khách đã nhận được để riêng ở khu chờ xử lý (hang_tra_cho_huy) rồi lập phiếu xuất hủy;
- lượng này đã trừ khỏi tồn từ lúc bán nên phiếu hủy không trừ tồn lần nữa.
Tiền hoàn tính theo giá khách thực trả của dòng (đã trừ ưu đãi thành viên phân bổ cho dòng),
không gồm phí giao hàng.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import IntegerField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_quyen_ghi_chi_nhanh, kiem_tra_vai_tro
from ung_dung.kho.services.giao_dich import khoa_kho, ma_chung_tu
from ung_dung.thanh_toan.services.doi_soat import cap_nhat_trang_thai_thanh_toan, so_tien_da_thu
from ung_dung.thanh_toan.services.ghi import ghi_ngay

from ..models import (
    AnhTraHang,
    ChiTietPhieuHoanKho,
    ChiTietTraHang,
    DonHang,
    HangTraChoHuy,
    LichSuDonHang,
    PhanBoPhieuBan,
    PhanBoTraHang,
    YeuCauTraHang,
)
from .dat_hang import KY_TU_MA_DON
from .thong_bao_don import bao_tra_hang

NGAY_DUOC_TRA = 7
SO_ANH_TOI_DA = 4
TRANG_THAI_MO = ("cho_duyet", "da_duyet")


def thoi_diem_hoan_thanh(don):
    lich_su = (
        LichSuDonHang.objects.filter(don_hang=don, den_trang_thai="hoan_thanh")
        .order_by("-thoi_diem_tao")
        .first()
    )
    return lich_su.thoi_diem_tao if lich_su else None


def han_tra_hang(don):
    xong = thoi_diem_hoan_thanh(don)
    return xong + timedelta(days=NGAY_DUOC_TRA) if xong else None


def ly_do_khong_tra_duoc(don):
    """Chuỗi giải thích vì sao đơn chưa gửi yêu cầu được; None nếu được gửi."""
    if don.trang_thai != "hoan_thanh":
        return "Chỉ gửi yêu cầu trả hàng cho đơn đã hoàn thành."
    han = han_tra_hang(don)
    if han is None or han < timezone.now():
        return f"Đã quá {NGAY_DUOC_TRA} ngày kể từ khi nhận hàng."
    if don.cac_yeu_cau_tra_hang.filter(trang_thai__in=TRANG_THAI_MO).exists():
        return "Đơn đang có yêu cầu trả hàng chưa xử lý xong."
    if not any(con > 0 for con in so_luong_con_tra(don).values()):
        return "Các thuốc trong đơn đã được trả hết."
    return None


def so_luong_con_tra(don):
    """{id dòng đơn: số lượng còn trả được} trừ các yêu cầu không bị từ chối."""
    da_tra = dict(
        ChiTietTraHang.objects.filter(yeu_cau_tra_hang__don_hang=don)
        .exclude(yeu_cau_tra_hang__trang_thai="tu_choi")
        .values("chi_tiet_don_hang")
        .annotate(tong=Sum("so_luong"))
        .values_list("chi_tiet_don_hang", "tong")
    )
    return {dong.pk: dong.so_luong - da_tra.get(dong.pk, 0) for dong in don.cac_dong.all()}


def _tao_ma(thoi_diem):
    import secrets

    ngay = timezone.localtime(thoi_diem).strftime("%y%m%d")
    for _ in range(8):
        ma = "TH" + ngay + "".join(secrets.choice(KY_TU_MA_DON) for _ in range(5))
        if not YeuCauTraHang.objects.filter(ma_yeu_cau_tra_hang=ma).exists():
            return ma
    raise ValidationError("Chưa cấp được mã yêu cầu, vui lòng thử lại.")


@transaction.atomic
def tao_yeu_cau(nguoi, don, *, ly_do, mo_ta, cac_dong, cac_anh, hoan_tien=None):
    """`cac_dong`: {id dòng đơn: số lượng trả}; `cac_anh`: tệp ảnh minh chứng.

    `hoan_tien`: hinh_thuc_hoan_tien và thông tin tài khoản/ví khách muốn nhận tiền hoàn.
    """
    kiem_tra_vai_tro(nguoi, "khach_hang")
    don = DonHang.objects.select_for_update().get(pk=don.pk)
    if don.khach_hang_id != nguoi.pk:
        raise PermissionDenied("Đơn không thuộc tài khoản của bạn.")
    ly_do_chan = ly_do_khong_tra_duoc(don)
    if ly_do_chan:
        raise ValidationError(ly_do_chan)
    con_lai = so_luong_con_tra(don)
    cac_dong = {int(ma): int(luong) for ma, luong in cac_dong.items() if int(luong) > 0}
    if not cac_dong:
        raise ValidationError("Chọn ít nhất một thuốc và số lượng cần trả.")
    for ma, luong in cac_dong.items():
        if ma not in con_lai or luong > con_lai[ma]:
            raise ValidationError("Số lượng trả vượt số lượng đã mua.")
    if not cac_anh:
        raise ValidationError("Cần ít nhất một ảnh chụp tình trạng thuốc.")
    if len(cac_anh) > SO_ANH_TOI_DA:
        raise ValidationError(f"Tối đa {SO_ANH_TOI_DA} ảnh.")
    so_tien = tinh_tien_hoan(don, cac_dong)
    bay_gio = timezone.now()
    yeu_cau = YeuCauTraHang(
        ma_yeu_cau_tra_hang=_tao_ma(bay_gio),
        don_hang=don,
        ly_do=ly_do,
        mo_ta=mo_ta.strip(),
        so_tien_hoan=so_tien,
        **(hoan_tien or {"hinh_thuc_hoan_tien": "tai_quay"}),
    )
    yeu_cau.full_clean()
    yeu_cau.save()
    ChiTietTraHang.objects.bulk_create(
        ChiTietTraHang(yeu_cau_tra_hang=yeu_cau, chi_tiet_don_hang_id=ma, so_luong=luong)
        for ma, luong in sorted(cac_dong.items())
    )
    for thu_tu, tep in enumerate(cac_anh):
        anh = AnhTraHang(yeu_cau_tra_hang=yeu_cau, thu_tu=thu_tu)
        anh.gan_du_lieu(tep)
        anh.save()
    bao_tra_hang(yeu_cau)
    return yeu_cau


def _lam_tron(so):
    return Decimal(so).quantize(Decimal(1), rounding=ROUND_HALF_UP)


def phan_giam_cua_phan_tra(dong_don, so_luong_truoc, so_luong_tra):
    """Phần ưu đãi thành viên ứng với `so_luong_tra` đơn vị, sau `so_luong_truoc` đã trả.

    Tính theo lũy kế để trả nhiều lần vẫn cộng đúng bằng phần giảm của dòng.
    """
    giam = Decimal(dong_don.giam_gia_phan_bo)
    if not giam:
        return Decimal(0)
    tong = dong_don.so_luong
    return _lam_tron(giam * (so_luong_truoc + so_luong_tra) / tong) - _lam_tron(
        giam * so_luong_truoc / tong
    )


def tinh_tien_hoan(don, cac_dong, bo_qua_yeu_cau=None):
    """Tiền hoàn của lần trả: Σ (đơn giá × số trả − phần ưu đãi của số đó) theo từng dòng.

    Mỗi khoản hoàn đã có chỉ trừ một lần: phần giảm tính lũy kế theo số đã trả trước (các
    yêu cầu không bị từ chối), và tổng không vượt tiền hàng khách thực trả còn lại. Phí giao
    hàng không được hoàn theo trả hàng.
    """
    cac_yeu_cau_truoc = don.cac_yeu_cau_tra_hang.exclude(trang_thai="tu_choi")
    if bo_qua_yeu_cau is not None:
        cac_yeu_cau_truoc = cac_yeu_cau_truoc.exclude(pk=bo_qua_yeu_cau.pk)
    da_tra = dict(
        ChiTietTraHang.objects.filter(yeu_cau_tra_hang__in=cac_yeu_cau_truoc)
        .values("chi_tiet_don_hang")
        .annotate(tong=Sum("so_luong"))
        .values_list("chi_tiet_don_hang", "tong")
    )
    dong_don = {dong.pk: dong for dong in don.cac_dong.all()}
    tien = Decimal(0)
    for ma, luong in cac_dong.items():
        dong = dong_don[ma]
        tien += dong.don_gia * luong - phan_giam_cua_phan_tra(dong, da_tra.get(ma, 0), luong)
    da_hoan_truoc = cac_yeu_cau_truoc.aggregate(tong=Sum("so_tien_hoan", default=Decimal(0)))[
        "tong"
    ]
    con_lai = Decimal(don.tien_hang) - Decimal(don.giam_gia_thanh_vien) - da_hoan_truoc
    return max(min(tien, con_lai), Decimal(0))


def _khoa_yeu_cau(nguoi, yeu_cau, trang_thai):
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, yeu_cau.don_hang.chi_nhanh, "tra_hang.duyet")
    yeu_cau = (
        YeuCauTraHang.objects.select_for_update(of=("self",))
        .select_related("don_hang")
        .get(pk=yeu_cau.pk)
    )
    if yeu_cau.trang_thai != trang_thai:
        raise ValidationError("Yêu cầu đã được xử lý ở bước khác, hãy tải lại trang.")
    return yeu_cau


def cac_lo_da_xuat(yeu_cau):
    """{id dòng trả: [{phan_bo, con_tra_duoc}]} các lô đã xuất cho thuốc của dòng, lô gần hạn trước.

    `con_tra_duoc`: lượng của phân bổ chưa nhập lại, chưa chờ hủy và chưa hoàn kho.
    """
    don = yeu_cau.don_hang
    ket_qua = {}
    for dong in yeu_cau.cac_dong.select_related("chi_tiet_don_hang__thuoc"):
        cac_phan_bo = (
            PhanBoPhieuBan.objects.filter(
                chi_tiet_phieu_ban__phieu_ban__don_hang=don,
                chi_tiet_phieu_ban__thuoc=dong.chi_tiet_don_hang.thuoc,
            )
            .select_related("ton_kho__lo_thuoc", "ton_kho__chi_nhanh")
            # Ba Subquery riêng để tổng không bị nhân bản khi nối các quan hệ ngược.
            .annotate(
                da_nhap_lai=_tong_theo_phan_bo(PhanBoTraHang),
                da_cho_huy=_tong_theo_phan_bo(HangTraChoHuy),
                da_hoan_kho=_tong_theo_phan_bo(ChiTietPhieuHoanKho),
            )
            .order_by("ton_kho__lo_thuoc__ngay_het_han", "pk")
        )
        ket_qua[dong.pk] = [
            {
                "phan_bo": pb,
                "con_tra_duoc": pb.so_luong - pb.da_nhap_lai - pb.da_cho_huy - pb.da_hoan_kho,
            }
            for pb in cac_phan_bo
        ]
    return ket_qua


def phan_lo_goi_y(yeu_cau):
    """{(id dòng trả, id phân bổ): lượng chờ hủy} khi dòng chỉ xuất từ một lô.

    Đơn xuất nhiều lô thì không đoán: quản lý phải chọn lô in trên hộp khách trả.
    """
    goi_y = {}
    cac_lo = cac_lo_da_xuat(yeu_cau)
    for dong in yeu_cau.cac_dong.select_related("chi_tiet_don_hang__thuoc"):
        con = [muc for muc in cac_lo.get(dong.pk, []) if muc["con_tra_duoc"] > 0]
        if len(con) == 1:
            goi_y[(dong.pk, con[0]["phan_bo"].pk)] = dong.so_luong
    return goi_y


def _tong_theo_phan_bo(model):
    tong = (
        model.objects.filter(phan_bo_phieu_ban=OuterRef("pk"))
        .order_by()
        .values("phan_bo_phieu_ban")
        .annotate(tong=Sum("so_luong"))
        .values("tong")
    )
    return Coalesce(Subquery(tong, output_field=IntegerField()), 0)


def _so_nguyen(gia_tri):
    if isinstance(gia_tri, bool) or not isinstance(gia_tri, int) or gia_tri < 0:
        raise ValidationError("Số lượng theo lô phải là số nguyên không âm.")
    return gia_tri


def _xu_ly_hang_tra(yeu_cau, phan_lo):
    """Đưa hàng đã giao vào khu chờ hủy theo đúng lô và lượng khách trả."""
    khoa_kho(yeu_cau.don_hang.chi_nhanh, cho_phep_ngung=True)
    cac_lo = cac_lo_da_xuat(yeu_cau)
    for ma_dong, _ in phan_lo:
        if ma_dong not in cac_lo:
            raise ValidationError("Có dòng không thuộc yêu cầu trả hàng này.")
    for dong in yeu_cau.cac_dong.select_related("chi_tiet_don_hang__thuoc"):
        thuoc = dong.chi_tiet_don_hang.thuoc
        theo_lo = {muc["phan_bo"].pk: muc for muc in cac_lo[dong.pk]}
        tong_huy = 0
        for (ma_dong, ma_pb), so_luong in phan_lo.items():
            if ma_dong != dong.pk:
                continue
            so_luong = _so_nguyen(so_luong)
            if not so_luong:
                continue
            muc = theo_lo.get(ma_pb)
            if muc is None:
                raise ValidationError(f"{thuoc.ten_thuoc}: lô đã chọn không xuất cho đơn này.")
            if so_luong > muc["con_tra_duoc"]:
                raise ValidationError(
                    f"{thuoc.ten_thuoc}: lô {muc['phan_bo'].ton_kho.lo_thuoc.ma_lo_thuoc} chỉ "
                    f"còn {muc['con_tra_duoc']} đã xuất cho đơn."
                )
            HangTraChoHuy.objects.create(
                chi_tiet_tra_hang=dong, phan_bo_phieu_ban=muc["phan_bo"], so_luong=so_luong
            )
            tong_huy += so_luong
        if tong_huy != dong.so_luong:
            raise ValidationError(
                f"{thuoc.ten_thuoc}: khách trả {dong.so_luong}, hãy ghi đủ số lượng theo lô."
            )


@transaction.atomic
def duyet(nguoi, yeu_cau, ghi_chu="", phan_lo=None):
    """Duyệt sau khi nhận hàng. Đơn xuất nhiều lô cần chỉ định đúng lô khách trả."""
    yeu_cau = _khoa_yeu_cau(nguoi, yeu_cau, "cho_duyet")
    if phan_lo is None:
        phan_lo = phan_lo_goi_y(yeu_cau)
    _xu_ly_hang_tra(yeu_cau, phan_lo)
    yeu_cau.trang_thai = "da_duyet"
    yeu_cau.ghi_chu_xu_ly = ghi_chu.strip()
    yeu_cau.nguoi_xu_ly = nguoi
    yeu_cau.thoi_diem_xu_ly = timezone.now()
    yeu_cau.save()
    bao_tra_hang(yeu_cau)
    return yeu_cau


@transaction.atomic
def tu_choi(nguoi, yeu_cau, ly_do):
    if not ly_do.strip():
        raise ValidationError("Cần ghi lý do từ chối để khách nắm được.")
    yeu_cau = _khoa_yeu_cau(nguoi, yeu_cau, "cho_duyet")
    yeu_cau.trang_thai = "tu_choi"
    yeu_cau.ghi_chu_xu_ly = ly_do.strip()
    yeu_cau.nguoi_xu_ly = nguoi
    yeu_cau.thoi_diem_xu_ly = timezone.now()
    yeu_cau.save()
    bao_tra_hang(yeu_cau)
    return yeu_cau


@transaction.atomic
def hoan_tien_tra_hang(nguoi, yeu_cau, *, phuong_thuc, ma_tham_chieu=""):
    yeu_cau = _khoa_yeu_cau(nguoi, yeu_cau, "da_duyet")
    don = DonHang.objects.select_for_update().get(pk=yeu_cau.don_hang_id)
    mong_doi = {"tai_quay": "tien_mat", "chuyen_khoan": "chuyen_khoan", "momo": "momo"}
    if phuong_thuc != mong_doi[yeu_cau.hinh_thuc_hoan_tien]:
        raise ValidationError("Chọn đúng hình thức nhận tiền đã ghi trong yêu cầu của khách.")
    if so_tien_da_thu(don) < yeu_cau.so_tien_hoan:
        raise ValidationError("Chưa ghi nhận đủ tiền đã thu. Kiểm tra đối soát thanh toán của đơn.")
    if yeu_cau.so_tien_hoan > 0:
        ghi_ngay(
            loai="hoan",
            phuong_thuc=phuong_thuc,
            so_tien=yeu_cau.so_tien_hoan,
            don_hang=don,
            nguoi=nguoi,
            ma_tham_chieu=f"tra-{ma_tham_chieu}" if ma_tham_chieu else None,
            ghi_chu=f"Hoàn tiền trả hàng {yeu_cau.ma_yeu_cau_tra_hang}",
        )
    yeu_cau.trang_thai = "da_hoan_tien"
    yeu_cau.save(update_fields=["trang_thai"])
    cap_nhat_trang_thai_thanh_toan(don)
    bao_tra_hang(yeu_cau)
    return yeu_cau


@transaction.atomic
def lap_phieu_huy_hang_tra(nguoi, yeu_cau, ghi_chu=""):
    """Lập phiếu xuất hủy cho phần hàng trả đang chờ hủy của một yêu cầu.

    Hàng này đã trừ khỏi tồn từ lúc bán, nên phiếu chỉ ghi nhận việc hủy (lô, số lượng, người
    lập) mà không trừ tồn thêm; dòng chờ hủy chuyển sang đã hủy và trỏ tới phiếu.
    """
    from ung_dung.kho.models import ChiTietPhieuXuatHuy, PhieuXuatHuy

    don = yeu_cau.don_hang
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, don.chi_nhanh, "xuat_huy.tao")
    khoa_kho(don.chi_nhanh, cho_phep_ngung=True)
    cac_dong = list(
        HangTraChoHuy.objects.select_for_update()
        .filter(chi_tiet_tra_hang__yeu_cau_tra_hang=yeu_cau, trang_thai="cho_huy")
        .select_related("phan_bo_phieu_ban__ton_kho__lo_thuoc")
        .order_by("pk")
    )
    if not cac_dong:
        raise ValidationError("Yêu cầu này không còn hàng chờ hủy.")
    theo_lo = {}
    for dong in cac_dong:
        lo = dong.phan_bo_phieu_ban.ton_kho.lo_thuoc
        theo_lo[lo] = theo_lo.get(lo, 0) + dong.so_luong
    hom_nay = timezone.localdate()
    loai = "het_han" if all(lo.ngay_het_han < hom_nay for lo in theo_lo) else "hu_hong"
    ghi_chu = " ".join(str(ghi_chu or "").split())
    phieu = PhieuXuatHuy.objects.create(
        ma_phieu_xuat_huy=ma_chung_tu("PX"),
        chi_nhanh=don.chi_nhanh,
        nguoi_lap=nguoi,
        loai_xuat_huy=loai,
        co_tru_ton=False,
        ghi_chu=(
            f"Hủy hàng khách trả theo yêu cầu {yeu_cau.ma_yeu_cau_tra_hang} "
            f"(đơn {don.ma_don_hang}). Hàng đã trừ tồn khi bán nên phiếu này không trừ tồn "
            f"lần nữa.{' ' + ghi_chu if ghi_chu else ''}"
        ),
    )
    for lo, so_luong in theo_lo.items():
        ChiTietPhieuXuatHuy.objects.create(phieu_xuat_huy=phieu, lo_thuoc=lo, so_luong=so_luong)
    HangTraChoHuy.objects.filter(pk__in=[dong.pk for dong in cac_dong]).update(
        trang_thai="da_huy", phieu_xuat_huy=phieu
    )
    return phieu
