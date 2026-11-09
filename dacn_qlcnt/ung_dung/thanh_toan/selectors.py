from django.conf import settings

from . import momo
from .models import GiaoDichThanhToan


def chuyen_khoan_da_cau_hinh():
    return bool(settings.NGAN_HANG_BIN and settings.SO_TAI_KHOAN and settings.TEN_TAI_KHOAN)


def phuong_thuc_kha_dung():
    """Phương thức trả trước chỉ bật khi đã cấu hình tài khoản nhận tiền."""
    kha_dung = {"cod"}
    if chuyen_khoan_da_cau_hinh():
        kha_dung.add("chuyen_khoan")
    if momo.da_cau_hinh():
        kha_dung.add("momo")
    return kha_dung


def giao_dich_cua_don(don):
    return GiaoDichThanhToan.objects.filter(don_hang=don).select_related("nguoi_xac_nhan")
