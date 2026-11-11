from django.apps import apps
from django.db.models import BigIntegerField, Case, F, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from ung_dung.chung.permissions import thay_toan_chuoi

from .models import LoThuoc, PhieuDieuChuyen, TonKho


def lay_so_du(*, nguoi=None, chi_nhanh=None, bo_qua_don=None):
    dang_giu = Value(0)
    if apps.is_installed("ung_dung.ban_hang"):
        from ung_dung.ban_hang.models import TRANG_THAI_GIU

        PhanBoDonHang = apps.get_model("ban_hang", "PhanBoDonHang")
        giu = PhanBoDonHang.objects.filter(
            ton_kho_id=OuterRef("pk"),
            chi_tiet_don_hang__don_hang__trang_thai__in=TRANG_THAI_GIU,
            chi_tiet_don_hang__don_hang__thoi_diem_het_giu__gt=timezone.now(),
        )
        if bo_qua_don:
            giu = giu.exclude(chi_tiet_don_hang__don_hang=bo_qua_don)
        giu = giu.values("ton_kho_id").annotate(tong=Sum("so_luong")).values("tong")
        dang_giu = Coalesce(
            Subquery(giu, output_field=BigIntegerField()), 0, output_field=BigIntegerField()
        )
    tap_hop = (
        TonKho.objects.select_related(
            "chi_nhanh", "lo_thuoc__thuoc__don_vi_tinh", "lo_thuoc__thuoc__nhom_atc"
        )
        .annotate(dang_giu=dang_giu)
        .annotate(kha_dung=F("so_luong") - F("dang_giu"))
    )
    if nguoi is not None and not thay_toan_chuoi(nguoi):
        tap_hop = tap_hop.filter(chi_nhanh_id=nguoi.chi_nhanh_id)
    if chi_nhanh is not None:
        tap_hop = tap_hop.filter(chi_nhanh=chi_nhanh)
    return tap_hop


def dieu_kien_lo_hop_le(con_han_den=None):
    """Lô bán được hôm nay (Q04: còn hiệu lực hết ngày hết hạn theo giờ Việt Nam).

    `con_han_den`: ngày lô phải còn hạn tới, ví dụ ngày hết giữ của đơn hoặc ngày tối thiểu
    của đơn giao hàng; không truyền thì chỉ cần còn hạn hôm nay.
    """
    hom_nay = timezone.localdate()
    return Q(
        lo_thuoc__ngay_het_han__gte=max(hom_nay, con_han_den or hom_nay),
        lo_thuoc__duoc_phep_ban=True,
        lo_thuoc__thuoc__dang_hoat_dong=True,
        chi_nhanh__dang_hoat_dong=True,
    )


def lay_ton_kha_dung(*, con_han_den=None, **tham_so):
    return lay_so_du(**tham_so).filter(dieu_kien_lo_hop_le(con_han_den))


def lay_giu_mo_coi(*, chi_nhanh=None, cac_chi_nhanh=None, bo_qua_don=None):
    """{(id chi nhánh, id thuốc): lượng} đơn còn hiệu lực đang giữ trên lô không bán được nữa.

    Lô hết hạn sau khi đặt hoặc bị khóa bán thì lay_ton_kha_dung loại cả lô, nên phần giữ
    trên lô đó không còn chắn lô khác. Đơn vẫn được hứa đủ hàng (Q03), vì vậy lượng này
    được trừ thêm vào tổng bán được của các lô hợp lệ cùng thuốc tại chi nhánh cho tới khi
    phần giữ được phân bổ lại (ban_hang.services.giu_hang).
    """
    if not apps.is_installed("ung_dung.ban_hang"):
        return {}
    from ung_dung.ban_hang.models import TRANG_THAI_GIU

    PhanBoDonHang = apps.get_model("ban_hang", "PhanBoDonHang")
    hom_nay = timezone.localdate()
    tap_hop = PhanBoDonHang.objects.filter(
        chi_tiet_don_hang__don_hang__trang_thai__in=TRANG_THAI_GIU,
        chi_tiet_don_hang__don_hang__thoi_diem_het_giu__gt=timezone.now(),
        ton_kho__lo_thuoc__thuoc__dang_hoat_dong=True,
        ton_kho__chi_nhanh__dang_hoat_dong=True,
    ).filter(
        Q(ton_kho__lo_thuoc__ngay_het_han__lt=hom_nay) | Q(ton_kho__lo_thuoc__duoc_phep_ban=False)
    )
    if chi_nhanh is not None:
        tap_hop = tap_hop.filter(ton_kho__chi_nhanh=chi_nhanh)
    if cac_chi_nhanh is not None:
        tap_hop = tap_hop.filter(ton_kho__chi_nhanh__in=cac_chi_nhanh)
    if bo_qua_don:
        tap_hop = tap_hop.exclude(chi_tiet_don_hang__don_hang=bo_qua_don)
    return {
        (dong["ton_kho__chi_nhanh_id"], dong["ton_kho__lo_thuoc__thuoc_id"]): dong["tong"]
        for dong in tap_hop.order_by()
        .values("ton_kho__chi_nhanh_id", "ton_kho__lo_thuoc__thuoc_id")
        .annotate(tong=Sum("so_luong"))
    }


def luong_ban_duoc(cac_chi_nhanh, cac_thuoc, *, con_han_den=None, bo_qua_don=None):
    """{(id chi nhánh, id thuốc): lượng còn bán được} sau khi trừ cả phần giữ mồ côi.

    Lượng lấy được từ các lô đạt `con_han_den` không vượt tổng của mọi lô bán được hôm nay
    trừ phần giữ mồ côi, để đơn giao (cần lô xa hạn) không lấy mất hàng đã hứa cho đơn khác.
    """

    def tong(con_han):
        return {
            (dong["chi_nhanh_id"], dong["lo_thuoc__thuoc_id"]): dong["luong"]
            for dong in lay_ton_kha_dung(con_han_den=con_han, bo_qua_don=bo_qua_don)
            .filter(chi_nhanh__in=cac_chi_nhanh, lo_thuoc__thuoc_id__in=cac_thuoc, kha_dung__gt=0)
            .order_by()
            .values("chi_nhanh_id", "lo_thuoc__thuoc_id")
            .annotate(luong=Sum("kha_dung"))
        }

    hom_nay = tong(None)
    du_han = tong(con_han_den) if con_han_den else hom_nay
    mo_coi = lay_giu_mo_coi(cac_chi_nhanh=cac_chi_nhanh, bo_qua_don=bo_qua_don)
    return {
        khoa: max(min(du_han.get(khoa, 0), luong - mo_coi.get(khoa, 0)), 0)
        for khoa, luong in hom_nay.items()
    }


def _nhu_cau(cac_dong):
    nhu_cau = {}
    for dong in cac_dong:
        ma = dong["thuoc"].pk
        nhu_cau[ma] = nhu_cau.get(ma, 0) + dong["so_luong"]
    return nhu_cau


def loc_chi_nhanh_du_thuoc(cac_chi_nhanh, cac_dong, *, con_han_den=None):
    """Chi nhánh còn đủ toàn bộ đơn; `con_han_den` giống mốc dùng khi giữ hàng thật."""
    nhu_cau = _nhu_cau(cac_dong)
    bang = luong_ban_duoc(cac_chi_nhanh, nhu_cau, con_han_den=con_han_den)
    return [
        cn
        for cn in cac_chi_nhanh
        if all(bang.get((cn.pk, ma), 0) >= luong for ma, luong in nhu_cau.items())
    ]


def thuoc_thieu(cac_chi_nhanh, cac_dong, *, con_han_den=None):
    """Thuốc không chi nhánh nào đủ: [{thuoc, can, nhieu_nhat, chi_nhanh}], để báo khách."""
    nhu_cau = _nhu_cau(cac_dong)
    bang = luong_ban_duoc(cac_chi_nhanh, nhu_cau, con_han_den=con_han_den)
    theo_ma = {dong["thuoc"].pk: dong["thuoc"] for dong in cac_dong}
    ket_qua = []
    for ma, can in nhu_cau.items():
        tot_nhat = max(
            ((bang.get((cn.pk, ma), 0), cn) for cn in cac_chi_nhanh),
            key=lambda cap: cap[0],
            default=(0, None),
        )
        if tot_nhat[0] < can:
            ket_qua.append(
                {
                    "thuoc": theo_ma[ma],
                    "can": can,
                    "nhieu_nhat": tot_nhat[0],
                    "chi_nhanh": tot_nhat[1],
                }
            )
    return ket_qua


def lay_bang_ton(nguoi):
    return (
        lay_so_du(nguoi=nguoi)
        .annotate(
            kha_dung_hop_le=Case(
                When(dieu_kien_lo_hop_le(), then=F("kha_dung")),
                default=0,
                output_field=BigIntegerField(),
            )
        )
        .order_by("chi_nhanh__ma_chi_nhanh", "lo_thuoc__ngay_het_han")
    )


def lay_ton_kiem_ke(chi_nhanh, *, tu_khoa="", chi_con_hang=False):
    tap_hop = TonKho.objects.filter(chi_nhanh=chi_nhanh).select_related(
        "lo_thuoc__thuoc__don_vi_tinh"
    )
    if chi_con_hang:
        tap_hop = tap_hop.filter(so_luong__gt=0)
    if tu_khoa:
        tap_hop = tap_hop.filter(
            Q(lo_thuoc__ma_lo_thuoc__icontains=tu_khoa)
            | Q(lo_thuoc__thuoc__ten_thuoc__icontains=tu_khoa)
            | Q(lo_thuoc__thuoc__ma_thuoc__icontains=tu_khoa)
        )
    return tap_hop.order_by("lo_thuoc__thuoc__ten_thuoc", "lo_thuoc__ngay_het_han", "pk")


def lay_canh_bao_ton_thap(nguoi, *, chi_nhanh_id="", danh_muc_id="", tim=""):
    """(chi nhánh, thuốc) có lượng bán được dưới ngưỡng; lọc theo chi nhánh, danh mục, từ khóa."""
    from ung_dung.danh_muc.models import Thuoc
    from ung_dung.danh_muc.selectors import lay_chi_nhanh

    cac_chi_nhanh = lay_chi_nhanh(nguoi)
    if chi_nhanh_id:
        cac_chi_nhanh = cac_chi_nhanh.filter(pk=chi_nhanh_id)
    cac_canh_bao = []
    for chi_nhanh in cac_chi_nhanh:
        luong = (
            lay_ton_kha_dung(chi_nhanh=chi_nhanh)
            .filter(lo_thuoc__thuoc_id=OuterRef("pk"))
            .order_by()
            .values("lo_thuoc__thuoc_id")
            .annotate(tong=Sum("kha_dung"))
            .values("tong")
        )
        cac_thuoc = (
            Thuoc.objects.filter(dang_hoat_dong=True, nguong_canh_bao__gt=0)
            .select_related("don_vi_tinh")
            .annotate(
                kha_dung=Coalesce(
                    Subquery(luong, output_field=BigIntegerField()),
                    0,
                    output_field=BigIntegerField(),
                )
            )
            .filter(kha_dung__lt=F("nguong_canh_bao"))
            .order_by("kha_dung", "ma_thuoc")
        )
        if danh_muc_id:
            cac_thuoc = cac_thuoc.filter(danh_muc_san_pham_id=danh_muc_id)
        if tim:
            cac_thuoc = cac_thuoc.filter(Q(ten_thuoc__icontains=tim) | Q(ma_thuoc__icontains=tim))
        cac_canh_bao.extend((chi_nhanh, thuoc) for thuoc in cac_thuoc)
    return cac_canh_bao


def lay_canh_bao(nguoi):
    from datetime import timedelta

    cac_dong = list(lay_so_du(nguoi=nguoi).order_by("lo_thuoc__ngay_het_han"))
    hom_nay = timezone.localdate()
    return [
        dong
        for dong in cac_dong
        if dong.so_luong
        and (
            dong.lo_thuoc.ngay_het_han <= hom_nay + timedelta(days=30)
            or not dong.lo_thuoc.duoc_phep_ban
        )
    ]


def lay_phieu(nguoi, model, duong_dan="chi_nhanh"):
    tap_hop = model.objects.all().order_by("-thoi_diem_tao", "-pk")
    if not thay_toan_chuoi(nguoi):
        tap_hop = tap_hop.filter(**{f"{duong_dan}_id": nguoi.chi_nhanh_id})
    return tap_hop


def lay_phieu_dieu_chuyen(nguoi):
    """Phiếu điều chuyển chi nhánh được xem: cả phiếu chuyển đi lẫn phiếu chuyển đến."""
    tap_hop = PhieuDieuChuyen.objects.all().order_by("-thoi_diem_tao", "-pk")
    if not thay_toan_chuoi(nguoi):
        tap_hop = tap_hop.filter(
            Q(chi_nhanh_nguon_id=nguoi.chi_nhanh_id) | Q(chi_nhanh_dich_id=nguoi.chi_nhanh_id)
        )
    return tap_hop


def lay_cac_lo(nguoi):
    cac_lo = LoThuoc.objects.select_related("thuoc").order_by("ngay_het_han", "ma_lo_thuoc")
    if not thay_toan_chuoi(nguoi):
        cac_lo = cac_lo.filter(tonkho__chi_nhanh_id=nguoi.chi_nhanh_id).distinct()
    return cac_lo


def lay_lo_kem_ton(nguoi):
    """Lô thuốc kèm tổng lượng còn trong các kho người xem phụ trách."""
    from ung_dung.danh_muc.selectors import lay_chi_nhanh

    ton = (
        TonKho.objects.filter(lo_thuoc=OuterRef("pk"), chi_nhanh__in=lay_chi_nhanh(nguoi))
        .order_by()
        .values("lo_thuoc")
        .annotate(tong=Sum("so_luong"))
        .values("tong")
    )
    return lay_cac_lo(nguoi).annotate(
        tong_ton=Coalesce(Subquery(ton, output_field=BigIntegerField()), 0)
    )


def lay_lo_het_han_con_ton(chi_nhanh):
    """Lô đã qua ngày hết hạn còn tồn khả dụng, để lập sẵn phiếu xuất hủy."""
    return (
        lay_so_du(chi_nhanh=chi_nhanh)
        .filter(lo_thuoc__ngay_het_han__lt=timezone.localdate(), kha_dung__gt=0)
        .order_by("lo_thuoc__ngay_het_han", "lo_thuoc__ma_lo_thuoc")
    )


# Mức cảnh báo theo độ gấp; thứ tự trong bộ này là thứ tự hiển thị trên trang Cảnh báo kho.
MUC_CANH_BAO = (
    ("het_han", "Đã hết hạn", "Không được bán. Tách khỏi kệ và lập phiếu xuất hủy."),
    ("duoi_7", "Hết hạn trong 7 ngày", "Ưu tiên bán trước hoặc trả nhà cung cấp nếu còn được."),
    ("duoi_30", "Hết hạn trong 30 ngày", "Theo dõi; khi bán hệ thống tự lấy lô gần hạn trước."),
    ("khoa_ban", "Đang khóa bán", "Lô bị khóa bán. Chờ quản lý kiểm tra và mở khóa hoặc xuất hủy."),
)


def lo_theo_muc_canh_bao(tap_hop, muc):
    """Lọc số dư lô còn hàng theo một mức cảnh báo; dùng cho từng thẻ của trang cảnh báo.

    Thứ tự ưu tiên: đã hết hạn > đang khóa bán > hết hạn trong 7 ngày > trong 30 ngày.
    """
    from datetime import timedelta

    hom_nay = timezone.localdate()
    tap_hop = tap_hop.filter(so_luong__gt=0)
    if muc == "het_han":
        return tap_hop.filter(lo_thuoc__ngay_het_han__lt=hom_nay)
    con_han = tap_hop.filter(lo_thuoc__ngay_het_han__gte=hom_nay)
    if muc == "khoa_ban":
        return con_han.filter(lo_thuoc__duoc_phep_ban=False)
    dang_ban = con_han.filter(lo_thuoc__duoc_phep_ban=True)
    if muc == "duoi_7":
        return dang_ban.filter(lo_thuoc__ngay_het_han__lte=hom_nay + timedelta(days=7))
    return dang_ban.filter(
        lo_thuoc__ngay_het_han__gt=hom_nay + timedelta(days=7),
        lo_thuoc__ngay_het_han__lte=hom_nay + timedelta(days=30),
    )


def lay_phieu_nhap_danh_sach(nguoi):
    """Phiếu nhập kèm nhà cung cấp và tổng giá trị nhập, cho trang danh sách."""
    from django.db.models import DecimalField, ExpressionWrapper

    from .models import ChiTietPhieuNhap, PhieuNhap

    dong = (
        ChiTietPhieuNhap.objects.filter(phieu_nhap=OuterRef("pk")).order_by().values("phieu_nhap")
    )
    tien = ExpressionWrapper(F("so_luong") * F("don_gia"), output_field=DecimalField())
    return (
        lay_phieu(nguoi, PhieuNhap)
        .select_related("nha_cung_cap")
        .annotate(
            ten_nha_cung_cap=F("nha_cung_cap__ten_nha_cung_cap"),
            gia_tri_nhap=Subquery(
                dong.annotate(t=Sum(tien)).values("t"), output_field=DecimalField()
            ),
        )
    )
