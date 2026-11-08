from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from ung_dung.chung.permissions import kiem_tra_vai_tro

from .models import DiaChiGiaoHang


def lay_tai_khoan(nguoi):
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
    return get_user_model().objects.select_related("chi_nhanh").order_by("ten_dang_nhap")


def cac_dia_chi_cua(nguoi):
    kiem_tra_vai_tro(nguoi, "khach_hang")
    return DiaChiGiaoHang.objects.filter(tai_khoan=nguoi).order_by("-thoi_diem_tao")


def lay_dia_chi_cua(nguoi, pk):
    return get_object_or_404(cac_dia_chi_cua(nguoi), pk=pk)
