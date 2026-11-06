from django.contrib.auth import get_user_model
from django.db import DEFAULT_DB_ALIAS, transaction

from ung_dung.chung.van_ban import cat_khoang_trang


def tao_tai_khoan_ky_thuat(
    ten_dang_nhap,
    mat_khau=None,
    *,
    dang_hoat_dong=True,
    la_quan_tri_he_thong=False,
    co_so_du_lieu=None,
):
    if not isinstance(ten_dang_nhap, str):
        raise ValueError("Tên đăng nhập phải là văn bản.")
    ten_dang_nhap = cat_khoang_trang(ten_dang_nhap)
    if not ten_dang_nhap:
        raise ValueError("Tên đăng nhập không được rỗng.")
    co_so_du_lieu = co_so_du_lieu or DEFAULT_DB_ALIAS
    with transaction.atomic(using=co_so_du_lieu):
        tai_khoan = get_user_model()(
            ten_dang_nhap=ten_dang_nhap,
            dang_hoat_dong=dang_hoat_dong,
            la_quan_tri_he_thong=la_quan_tri_he_thong,
        )
        tai_khoan.set_password(mat_khau)
        tai_khoan.save(using=co_so_du_lieu)
        return tai_khoan
