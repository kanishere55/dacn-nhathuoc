from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS, transaction

from ung_dung.chung.permissions import kiem_tra_vai_tro
from ung_dung.chung.van_ban import cat_khoang_trang


def tao_tai_khoan_ky_thuat(
    ten_dang_nhap,
    mat_khau=None,
    *,
    dang_hoat_dong=True,
    la_quan_tri_he_thong=False,
    co_so_du_lieu=None,
    vai_tro="khach_hang",
    chi_nhanh=None,
    **ho_so,
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
            vai_tro=vai_tro,
            chi_nhanh=chi_nhanh,
            **ho_so,
        )
        tai_khoan.set_password(mat_khau)
        tai_khoan.save(using=co_so_du_lieu)
        return tai_khoan


@transaction.atomic
def luu_tai_khoan(nguoi, du_lieu, doi_tuong=None):
    """Quản trị chuỗi tạo hoặc sửa tài khoản; email do quản trị nhập coi là đã xác thực."""
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
    model = get_user_model()
    tai_khoan = model.objects.select_for_update().get(pk=doi_tuong.pk) if doi_tuong else model()
    email_cu = tai_khoan.email
    for ten in ("ten_dang_nhap", "vai_tro", "chi_nhanh", "dang_hoat_dong", "ho_ten"):
        if ten in du_lieu:
            setattr(tai_khoan, ten, du_lieu[ten])
    if "so_dien_thoai" in du_lieu:
        tai_khoan.so_dien_thoai = du_lieu["so_dien_thoai"] or ""
    if "email" in du_lieu:
        tai_khoan.email = du_lieu["email"] or None
        if tai_khoan.email != email_cu:
            tai_khoan.da_xac_thuc_email = tai_khoan.email is not None
    if tai_khoan.pk == nguoi.pk and not tai_khoan.dang_hoat_dong:
        raise ValidationError("Không thể tự khóa tài khoản đang đăng nhập.")
    mat_khau = du_lieu.get("mat_khau")
    if mat_khau:
        validate_password(mat_khau, tai_khoan)
        tai_khoan.set_password(mat_khau)
    elif not tai_khoan.pk:
        raise ValidationError("Tài khoản mới cần có mật khẩu.")
    tai_khoan.full_clean()
    tai_khoan.save()
    return tai_khoan
