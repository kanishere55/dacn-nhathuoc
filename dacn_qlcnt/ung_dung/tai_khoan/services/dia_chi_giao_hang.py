from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from ung_dung.chung.permissions import kiem_tra_vai_tro

from ..models import DiaChiGiaoHang

SO_DIA_CHI_TOI_DA = 10


def _khoa_chu(nguoi):
    kiem_tra_vai_tro(nguoi, "khach_hang")
    return get_user_model().objects.select_for_update().get(pk=nguoi.pk)


def _lay_cua(chu, dia_chi):
    dia_chi = DiaChiGiaoHang.objects.select_for_update().filter(pk=dia_chi.pk).first()
    if dia_chi is None or dia_chi.tai_khoan_id != chu.pk:
        raise PermissionDenied("Địa chỉ không thuộc tài khoản của bạn.")
    return dia_chi


@transaction.atomic
def luu_dia_chi(nguoi, du_lieu, dia_chi=None):
    chu = _khoa_chu(nguoi)
    if dia_chi is None:
        if chu.cac_dia_chi_giao_hang.count() >= SO_DIA_CHI_TOI_DA:
            raise ValidationError(f"Sổ địa chỉ chỉ lưu tối đa {SO_DIA_CHI_TOI_DA} địa chỉ.")
        dia_chi = DiaChiGiaoHang(tai_khoan=chu)
    else:
        dia_chi = _lay_cua(chu, dia_chi)
    for ten in ("ten_nguoi_nhan", "so_dien_thoai", "dia_chi", "ghi_chu"):
        setattr(dia_chi, ten, du_lieu[ten])
    dia_chi.vi_tri = Point(float(du_lieu["kinh_do"]), float(du_lieu["vi_do"]), srid=4326)
    dia_chi.save()
    if chu.dia_chi_giao_hang_mac_dinh_id is None or du_lieu.get("dat_mac_dinh"):
        chu.dia_chi_giao_hang_mac_dinh = dia_chi
        chu.save(update_fields=["dia_chi_giao_hang_mac_dinh"])
    return dia_chi


@transaction.atomic
def dat_mac_dinh(nguoi, dia_chi):
    chu = _khoa_chu(nguoi)
    chu.dia_chi_giao_hang_mac_dinh = _lay_cua(chu, dia_chi)
    chu.save(update_fields=["dia_chi_giao_hang_mac_dinh"])


@transaction.atomic
def xoa_dia_chi(nguoi, dia_chi):
    chu = _khoa_chu(nguoi)
    dia_chi = _lay_cua(chu, dia_chi)
    if chu.dia_chi_giao_hang_mac_dinh_id == dia_chi.pk:
        chu.dia_chi_giao_hang_mac_dinh = (
            chu.cac_dia_chi_giao_hang.exclude(pk=dia_chi.pk).order_by("-thoi_diem_tao").first()
        )
        chu.save(update_fields=["dia_chi_giao_hang_mac_dinh"])
    dia_chi.delete()
