from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.thong_bao.services import gui_email

from .xac_thuc import bao_doi_mat_khau

NHAN_TRUONG = {"ho_ten": "họ tên", "so_dien_thoai": "số điện thoại"}


@transaction.atomic
def cap_nhat_ho_so(nguoi, *, ho_ten, so_dien_thoai):
    tai_khoan = get_user_model().objects.select_for_update().get(pk=nguoi.pk)
    moi = {"ho_ten": ho_ten, "so_dien_thoai": so_dien_thoai}
    cac_muc_doi = [
        NHAN_TRUONG[ten] for ten, gia_tri in moi.items() if getattr(tai_khoan, ten) != gia_tri
    ]
    if not cac_muc_doi:
        return tai_khoan
    for ten, gia_tri in moi.items():
        setattr(tai_khoan, ten, gia_tri)
    tai_khoan.save(update_fields=list(moi))
    if tai_khoan.email:
        gui_email(
            loai_email="ho_so_da_doi",
            email_nhan=tai_khoan.email,
            tai_khoan=tai_khoan,
            tieu_de="Hồ sơ tài khoản vừa được cập nhật",
            mau="ho_so_da_doi",
            ngu_canh={
                "ho_ten": tai_khoan.ho_ten,
                "ten_dang_nhap": tai_khoan.ten_dang_nhap,
                "cac_muc_doi": cac_muc_doi,
                "thoi_diem": timezone.localtime(),
            },
        )
    return tai_khoan


@transaction.atomic
def doi_mat_khau(nguoi, mat_khau_hien_tai, mat_khau_moi):
    tai_khoan = get_user_model().objects.select_for_update().get(pk=nguoi.pk)
    if not tai_khoan.check_password(mat_khau_hien_tai):
        raise ValidationError("Mật khẩu hiện tại không đúng.")
    if mat_khau_hien_tai == mat_khau_moi:
        raise ValidationError("Mật khẩu mới phải khác mật khẩu hiện tại.")
    validate_password(mat_khau_moi, tai_khoan)
    tai_khoan.set_password(mat_khau_moi)
    tai_khoan.save(update_fields=["password"])
    bao_doi_mat_khau(tai_khoan, "đổi trong trang tài khoản")
    return tai_khoan
