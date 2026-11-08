from django.db.models import Case, DecimalField, F, Q, Sum, Value, When
from django.db.models.functions import Now

from ung_dung.chung.permissions import la_quan_tri
from ung_dung.danh_muc.models import Thuoc

from .gio_dat_giu import KHOA_GIO
from .models import ChiTietPhieuBan, DonDatGiu, PhieuBan


def lay_gio(phien):
    return phien.get(KHOA_GIO, {})


def lay_dong_gio(gio):
    cac_thuoc = Thuoc.objects.select_related("don_vi_tinh").in_bulk([int(ma) for ma in gio])
    return [
        {"id_thuoc": int(ma), "thuoc": cac_thuoc.get(int(ma)), "so_luong": so_luong}
        for ma, so_luong in gio.items()
    ]


def gio_duoc_giu(cac_dong):
    return bool(cac_dong) and all(
        dong["thuoc"] and dong["thuoc"].dang_hoat_dong for dong in cac_dong
    )


def lay_don(nguoi):
    tap_hop = (
        DonDatGiu.objects.select_related("chi_nhanh", "khach_hang")
        .annotate(
            con_hieu_luc=Q(trang_thai="dang_giu", thoi_diem_het_giu__gt=Now()),
            nhan_trang_thai=Case(
                When(trang_thai="dang_giu", thoi_diem_het_giu__gt=Now(), then=Value("Đang giữ")),
                When(trang_thai="da_huy", then=Value("Đã hủy")),
                When(trang_thai="da_nhan", then=Value("Đã nhận tại quầy")),
                default=Value("Hết hạn"),
            ),
        )
        .order_by("-pk")
    )
    if not la_quan_tri(nguoi):
        tap_hop = tap_hop.filter(
            **(
                {"khach_hang": nguoi}
                if nguoi.vai_tro == "khach_hang"
                else {"chi_nhanh_id": nguoi.chi_nhanh_id}
            )
        )
    return tap_hop


def lay_chi_tiet_don(don):
    return don.chitietdondatgiu_set.select_related("thuoc__don_vi_tinh").order_by("pk")


def lay_phieu_ban(nguoi):
    tap_hop = PhieuBan.objects.select_related("chi_nhanh", "nguoi_lap").order_by("-pk")
    if not la_quan_tri(nguoi):
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
