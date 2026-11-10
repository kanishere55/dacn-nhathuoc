"""Trả hàng: khách gửi yêu cầu cho đơn đã hoàn thành, quản lý chi nhánh duyệt và hoàn tiền.

Thuốc đã bán chỉ nhận trả khi lỗi thuộc nhà thuốc (giao sai, hư hỏng, hết hạn). Khi duyệt,
quản lý đã nhận lại hàng và kiểm từng dòng: phần còn nguyên niêm phong (thường là thuốc giao
nhầm) được nhập lại đúng các lô đã xuất cho đơn, ghi vào phan_bo_tra_hang để truy vết; phần
hư hỏng hoặc hết hạn không nhập lại tồn bán vì lượng đó đã trừ khỏi kho từ lúc bán.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import IntegerField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_quyen_ghi_chi_nhanh, kiem_tra_vai_tro
from ung_dung.kho.services.giao_dich import khoa_kho, thay_doi_ton
from ung_dung.thanh_toan.services.cong import so_tien_da_thu
from ung_dung.thanh_toan.services.ghi import ghi_ngay

from ..models import (
    AnhTraHang,
    ChiTietPhieuHoanKho,
    ChiTietTraHang,
    DonHang,
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
    dong_don = {dong.pk: dong for dong in don.cac_dong.all()}
    tien_hang = sum((dong_don[ma].don_gia * luong for ma, luong in cac_dong.items()), Decimal(0))
    da_hoan = sum(
        (yc.so_tien_hoan for yc in don.cac_yeu_cau_tra_hang.filter(trang_thai="da_hoan_tien")),
        Decimal(0),
    )
    so_tien = min(tien_hang, max(so_tien_da_thu(don) - da_hoan, Decimal(0)))
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


def _khoa_yeu_cau(nguoi, yeu_cau, trang_thai):
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, yeu_cau.don_hang.chi_nhanh, "tra_hang.duyet")
    yeu_cau = (
        YeuCauTraHang.objects.select_for_update().select_related("don_hang").get(pk=yeu_cau.pk)
    )
    if yeu_cau.trang_thai != trang_thai:
        raise ValidationError("Yêu cầu đã được xử lý ở bước khác, hãy tải lại trang.")
    return yeu_cau


def so_luong_nhap_lai_goi_y(yeu_cau):
    """Thuốc giao nhầm còn nguyên thường bán lại được; hư hỏng, hết hạn thì không."""
    return {
        dong.pk: (dong.so_luong if yeu_cau.ly_do == "sai_san_pham" else 0)
        for dong in yeu_cau.cac_dong.all()
    }


def _tong_theo_phan_bo(model):
    tong = (
        model.objects.filter(phan_bo_phieu_ban=OuterRef("pk"))
        .order_by()
        .values("phan_bo_phieu_ban")
        .annotate(tong=Sum("so_luong"))
        .values("tong")
    )
    return Coalesce(Subquery(tong, output_field=IntegerField()), 0)


def _nhap_lai_kho(yeu_cau, nhap_lai):
    """Cộng lại tồn cho phần bán lại được, vào đúng các lô đã xuất cho đơn (lô hạn xa trước)."""
    don = yeu_cau.don_hang
    khoa_kho(don.chi_nhanh, cho_phep_ngung=True)
    for dong in yeu_cau.cac_dong.select_related("chi_tiet_don_hang__thuoc").order_by("pk"):
        so_luong = nhap_lai.get(dong.pk, 0)
        if isinstance(so_luong, bool) or not isinstance(so_luong, int):
            raise ValidationError("Số lượng nhập lại phải là số nguyên.")
        if so_luong < 0 or so_luong > dong.so_luong:
            raise ValidationError(
                f"Nhập lại {dong.chi_tiet_don_hang.thuoc.ten_thuoc} trong khoảng 0 đến {dong.so_luong}."
            )
        dong.so_luong_nhap_lai = so_luong
        dong.save(update_fields=["so_luong_nhap_lai"])
        con_lai = so_luong
        cac_phan_bo = (
            PhanBoPhieuBan.objects.filter(
                chi_tiet_phieu_ban__phieu_ban__don_hang=don,
                chi_tiet_phieu_ban__thuoc=dong.chi_tiet_don_hang.thuoc,
            )
            .select_related("ton_kho__lo_thuoc")
            # Hai Subquery riêng để tổng không bị nhân bản khi nối hai quan hệ ngược.
            .annotate(
                da_nhap_lai=_tong_theo_phan_bo(PhanBoTraHang),
                da_hoan_kho=_tong_theo_phan_bo(ChiTietPhieuHoanKho),
            )
            .order_by("-ton_kho__lo_thuoc__ngay_het_han", "-pk")
        )
        for phan_bo in cac_phan_bo:
            if not con_lai:
                break
            con_cho = phan_bo.so_luong - phan_bo.da_nhap_lai - phan_bo.da_hoan_kho
            lay = min(con_lai, con_cho)
            if lay <= 0:
                continue
            thay_doi_ton(phan_bo.ton_kho, lay)
            PhanBoTraHang.objects.create(
                chi_tiet_tra_hang=dong, phan_bo_phieu_ban=phan_bo, so_luong=lay
            )
            con_lai -= lay
        if con_lai:
            raise ValidationError(
                f"Lượng nhập lại của {dong.chi_tiet_don_hang.thuoc.ten_thuoc} vượt lượng đã xuất cho đơn."
            )


@transaction.atomic
def duyet(nguoi, yeu_cau, ghi_chu="", nhap_lai=None):
    """Quản lý đã nhận lại và kiểm hàng; số tiền hoàn giữ theo giá đã mua.

    `nhap_lai`: {id dòng trả: lượng còn bán được}; None dùng gợi ý theo lý do trả.
    """
    yeu_cau = _khoa_yeu_cau(nguoi, yeu_cau, "cho_duyet")
    _nhap_lai_kho(yeu_cau, so_luong_nhap_lai_goi_y(yeu_cau) if nhap_lai is None else nhap_lai)
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
    if so_tien_da_thu(don) <= 0:
        don.trang_thai_thanh_toan = "da_hoan_tien"
        don.save(update_fields=["trang_thai_thanh_toan"])
    bao_tra_hang(yeu_cau)
    return yeu_cau
