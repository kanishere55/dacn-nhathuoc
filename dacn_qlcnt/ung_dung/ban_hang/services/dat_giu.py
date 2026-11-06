from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_chi_nhanh, kiem_tra_vai_tro
from ung_dung.danh_muc.models import Thuoc
from ung_dung.kho.services.giao_dich import doi_ve_co_so, khoa_kho, ma_chung_tu, phan_bo_fefo

from ..models import ChiTietDonDatGiu, DonDatGiu, PhanBoDatGiu


@transaction.atomic
def dat_giu(nguoi, chi_nhanh, cac_dong):
    if not nguoi.is_authenticated or not nguoi.is_active or nguoi.vai_tro != "khach_hang":
        raise PermissionDenied("Chỉ tài khoản khách hàng được đặt giữ.")
    khoa_kho(chi_nhanh)
    if not cac_dong:
        raise ValidationError("Cần ít nhất một thuốc để đặt giữ.")
    yeu_cau = {}
    for dong in cac_dong:
        luong = dong["so_luong"]
        if isinstance(luong, bool) or not isinstance(luong, int) or luong <= 0:
            raise ValidationError("Số lượng phải là số nguyên dương.")
        ma = dong["thuoc"].pk
        yeu_cau[ma] = yeu_cau.get(ma, 0) + luong
    don = DonDatGiu.objects.create(
        ma_don_dat_giu=ma_chung_tu("DG"),
        khach_hang=nguoi,
        chi_nhanh=chi_nhanh,
        thoi_diem_het_giu=timezone.now() + timedelta(hours=24),
    )
    for ma, luong in sorted(yeu_cau.items()):
        thuoc = Thuoc.objects.get(pk=ma)
        chi_tiet = ChiTietDonDatGiu.objects.create(
            don_dat_giu=don, thuoc=thuoc, so_luong=doi_ve_co_so(thuoc, luong)
        )
        for ton, lay in phan_bo_fefo(chi_nhanh, thuoc, luong):
            PhanBoDatGiu.objects.create(chi_tiet_don_dat_giu=chi_tiet, ton_kho=ton, so_luong=lay)
    return don


@transaction.atomic
def huy_giu(nguoi, don):
    kiem_tra_vai_tro(nguoi, "khach_hang", "nhan_vien", "quan_ly_chi_nhanh")
    if nguoi.vai_tro == "khach_hang":
        if don.khach_hang_id != nguoi.pk:
            raise PermissionDenied("Đơn không thuộc bạn.")
    else:
        kiem_tra_chi_nhanh(nguoi, don.chi_nhanh)
    khoa_kho(don.chi_nhanh, cho_phep_ngung=True)
    don = DonDatGiu.objects.select_for_update().get(pk=don.pk)
    if don.trang_thai == "da_nhan":
        raise ValidationError("Đơn đã nhận không thể hủy.")
    if don.trang_thai == "dang_giu":
        don.trang_thai = "het_han" if don.thoi_diem_het_giu <= timezone.now() else "da_huy"
        don.save(update_fields=["trang_thai"])
    return don


def giai_phong_het_han():
    so_don = 0
    for ma in DonDatGiu.objects.filter(
        trang_thai="dang_giu", thoi_diem_het_giu__lte=timezone.now()
    ).values_list("pk", flat=True):
        with transaction.atomic():
            don = DonDatGiu.objects.select_related("chi_nhanh").get(pk=ma)
            khoa_kho(don.chi_nhanh, cho_phep_ngung=True)
            don = DonDatGiu.objects.select_for_update().get(pk=ma)
            if don.trang_thai == "dang_giu" and don.thoi_diem_het_giu <= timezone.now():
                don.trang_thai = "het_han"
                don.save(update_fields=["trang_thai"])
                so_don += 1
    return so_don
