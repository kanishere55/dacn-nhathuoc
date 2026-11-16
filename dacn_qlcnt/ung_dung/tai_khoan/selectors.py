from django.contrib.auth import get_user_model

from ung_dung.chung.permissions import kiem_tra_quyen


def lay_tai_khoan(nguoi):
    kiem_tra_quyen(nguoi, "tai_khoan.xem")
    return get_user_model().objects.select_related("chi_nhanh").order_by("ten_dang_nhap")
