from django.db.models import Case, Count, DecimalField, F, IntegerField, Q, Sum, When
from django.db.models.functions import Now

from ung_dung.chung.permissions import thay_toan_chuoi
from ung_dung.danh_muc.models import Thuoc
from ung_dung.danh_muc.selectors import them_gia_va_anh

from .gio_hang import KHOA_GIO
from .models import TRANG_THAI_GIU, ChiTietPhieuBan, DonHang, PhieuBan, YeuCauXuatHoaDon


def lay_gio(phien):
    return phien.get(KHOA_GIO, {})


def lay_dong_gio(gio):
    """Các dòng giỏ kèm giá đang áp dụng; thuốc đã ngừng kinh doanh có thuoc=None."""
    cac_thuoc = (
        them_gia_va_anh(Thuoc.objects.filter(dang_hoat_dong=True))
        .select_related("don_vi_tinh")
        .in_bulk([int(ma) for ma in gio])
    )
    cac_dong = []
    for ma, so_luong in gio.items():
        thuoc = cac_thuoc.get(int(ma))
        cac_dong.append(
            {
                "id_thuoc": int(ma),
                "thuoc": thuoc,
                "so_luong": so_luong,
                "thanh_tien": thuoc.don_gia * so_luong if thuoc else 0,
            }
        )
    return cac_dong


def gio_duoc_giu(cac_dong):
    return bool(cac_dong) and all(dong["thuoc"] for dong in cac_dong)


def tom_tat_gio(cac_dong):
    hop_le = [dong for dong in cac_dong if dong["thuoc"]]
    return {
        "tien_hang": sum(dong["thanh_tien"] for dong in hop_le),
        "so_luong": sum(dong["so_luong"] for dong in hop_le),
        "co_ke_don": any(dong["thuoc"].la_thuoc_ke_don for dong in hop_le),
        "hop_le": gio_duoc_giu(cac_dong),
    }


def lay_don(nguoi, *, trang_thai="", hinh_thuc_nhan="", tim=""):
    tap_hop = (
        DonHang.objects.select_related("chi_nhanh", "khach_hang")
        .annotate(
            con_hieu_luc=Q(trang_thai__in=TRANG_THAI_GIU, thoi_diem_het_giu__gt=Now()),
            qua_han_giu=Q(trang_thai__in=TRANG_THAI_GIU, thoi_diem_het_giu__lte=Now()),
        )
        .order_by("-pk")
    )
    if not thay_toan_chuoi(nguoi):
        tap_hop = tap_hop.filter(
            **(
                {"khach_hang": nguoi}
                if nguoi.vai_tro == "khach_hang"
                else {"chi_nhanh_id": nguoi.chi_nhanh_id}
            )
        )
    if trang_thai:
        tap_hop = tap_hop.filter(trang_thai=trang_thai)
    if hinh_thuc_nhan:
        tap_hop = tap_hop.filter(hinh_thuc_nhan=hinh_thuc_nhan)
    if tim:
        tap_hop = tap_hop.filter(
            Q(ma_don_hang__icontains=tim)
            | Q(khach_hang__ten_dang_nhap__icontains=tim)
            | Q(khach_hang__ho_ten__icontains=tim)
            | Q(so_dien_thoai_nhan__icontains=tim)
        )
    return tap_hop


def dem_don_theo_trang_thai(nguoi):
    return dict(
        lay_don(nguoi)
        .order_by()
        .values_list("trang_thai")
        .annotate(so=Count("pk"))
        .values_list("trang_thai", "so")
    )


def lay_chi_tiet_don(don):
    return don.cac_dong.select_related("thuoc__don_vi_tinh").order_by("pk")


def lay_lich_su(don):
    return don.cac_lich_su.select_related("nguoi_thuc_hien").order_by("thoi_diem_tao", "pk")


def lay_phieu_ban(nguoi):
    tap_hop = PhieuBan.objects.select_related("chi_nhanh", "nguoi_lap", "don_hang").order_by("-pk")
    if not thay_toan_chuoi(nguoi):
        tap_hop = tap_hop.filter(chi_nhanh_id=nguoi.chi_nhanh_id)
    return tap_hop


def chi_tiet_ban(phieu):
    return ChiTietPhieuBan.objects.filter(phieu_ban=phieu).annotate(
        thanh_tien=F("so_luong") * F("don_gia")
    )


def tong_tien_ban(phieu):
    return (
        chi_tiet_ban(phieu).aggregate(tong=Sum("thanh_tien", output_field=DecimalField()))["tong"]
        or 0
    )


def lay_yeu_cau_xuat_hoa_don(nguoi, *, trang_thai=""):
    """Yêu cầu hóa đơn công ty trong phạm vi chi nhánh; chờ xử lý lên đầu."""
    tap_hop = YeuCauXuatHoaDon.objects.select_related(
        "don_hang__chi_nhanh", "don_hang__khach_hang", "nguoi_xu_ly"
    ).order_by(
        # Yêu cầu chờ xử lý đứng đầu, rồi mới nhất trước.
        Case(When(trang_thai="cho_xu_ly", then=0), default=1, output_field=IntegerField()),
        "-thoi_diem_tao",
    )
    if not thay_toan_chuoi(nguoi):
        tap_hop = tap_hop.filter(don_hang__chi_nhanh_id=nguoi.chi_nhanh_id)
    if trang_thai:
        tap_hop = tap_hop.filter(trang_thai=trang_thai)
    return tap_hop
