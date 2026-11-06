from django.contrib.auth import get_user_model

from ung_dung.chung.permissions import kiem_tra_vai_tro


def lay_tai_khoan(nguoi):
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
    return get_user_model().objects.select_related("chi_nhanh").order_by("ten_dang_nhap")
