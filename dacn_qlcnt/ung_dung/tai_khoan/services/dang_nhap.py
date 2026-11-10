"""Giới hạn thử mật khẩu: 5 lần sai liên tiếp thì khóa đăng nhập tài khoản 15 phút.

Bộ đếm lưu ở cột tai_khoan.so_lan_dang_nhap_sai và thoi_diem_mo_khoa_dang_nhap.
Tên đăng nhập không tồn tại thì không có gì để đếm và vẫn chỉ nhận thông báo chung.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

SO_LAN_SAI_TOI_DA = 5
PHUT_KHOA = 15


def tim_tai_khoan(ten_dang_nhap):
    if not ten_dang_nhap:
        return None
    return get_user_model().objects.filter(ten_dang_nhap=ten_dang_nhap).first()


def thoi_diem_mo_khoa(tai_khoan):
    """Thời điểm mở khóa nếu tài khoản đang bị khóa đăng nhập, ngược lại None."""
    mo_khoa = tai_khoan.thoi_diem_mo_khoa_dang_nhap if tai_khoan else None
    return mo_khoa if mo_khoa and mo_khoa > timezone.now() else None


@transaction.atomic
def ghi_dang_nhap_sai(tai_khoan):
    tai_khoan = get_user_model().objects.select_for_update().get(pk=tai_khoan.pk)
    so_lan = tai_khoan.so_lan_dang_nhap_sai + 1
    if so_lan >= SO_LAN_SAI_TOI_DA:
        tai_khoan.so_lan_dang_nhap_sai = 0
        tai_khoan.thoi_diem_mo_khoa_dang_nhap = timezone.now() + timedelta(minutes=PHUT_KHOA)
    else:
        tai_khoan.so_lan_dang_nhap_sai = so_lan
    tai_khoan.save(update_fields=["so_lan_dang_nhap_sai", "thoi_diem_mo_khoa_dang_nhap"])
    return thoi_diem_mo_khoa(tai_khoan)


def xoa_dem_dang_nhap_sai(tai_khoan):
    if tai_khoan.so_lan_dang_nhap_sai or tai_khoan.thoi_diem_mo_khoa_dang_nhap:
        get_user_model().objects.filter(pk=tai_khoan.pk).update(
            so_lan_dang_nhap_sai=0, thoi_diem_mo_khoa_dang_nhap=None
        )
