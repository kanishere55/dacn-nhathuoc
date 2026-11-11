"""Quy tắc nghiệp vụ kho dùng chung cho form, nhập Excel và service (service quyết định cuối)."""

from datetime import date

from django.utils import timezone

from ung_dung.chung.van_ban import KY_TU_KHOANG_TRANG

# Hạn dùng xa hơn mốc này gần như chắc chắn là gõ nhầm năm (thuốc thường có hạn 2–5 năm).
SO_NAM_HAN_TOI_DA = 10
# Lô còn ít hơn số ngày này là cận hạn: người nhập phải xác nhận vẫn nhận (GPP: kiểm hạn khi nhập).
SO_NGAY_CAN_HAN = 90


def chuan_hoa_ma_lo(ma_lo):
    """Mã lô in trên bao bì: bỏ mọi khoảng trắng (kể cả ký tự vô hình) và viết hoa."""
    return "".join(ky_tu for ky_tu in str(ma_lo or "") if ky_tu not in KY_TU_KHOANG_TRANG).upper()


def han_toi_da(hom_nay=None):
    hom_nay = hom_nay or timezone.localdate()
    nam = hom_nay.year + SO_NAM_HAN_TOI_DA
    # 29/02 cộng 10 năm có thể không tồn tại: lùi về 28/02.
    return date(nam, hom_nay.month, min(hom_nay.day, 28 if hom_nay.month == 2 else 31))


def loi_han_dung(ngay_het_han, hom_nay=None):
    """Câu báo lỗi nếu hạn dùng không nhận được vào kho bán; None nếu hợp lệ."""
    hom_nay = hom_nay or timezone.localdate()
    if ngay_het_han <= hom_nay:
        return (
            f"Hạn dùng {ngay_het_han:%d/%m/%Y} đã qua hoặc hết trong hôm nay, không nhận vào "
            "kho bán. Nếu nhà cung cấp giao nhầm, hãy từ chối nhận lô này."
        )
    if ngay_het_han > han_toi_da(hom_nay):
        return (
            f"Hạn dùng {ngay_het_han:%d/%m/%Y} xa hơn {SO_NAM_HAN_TOI_DA} năm, có thể gõ nhầm "
            "năm. Hãy xem lại hạn in trên bao bì."
        )
    return None


def so_ngay_con_han(ngay_het_han, hom_nay=None):
    return (ngay_het_han - (hom_nay or timezone.localdate())).days


def la_can_han(ngay_het_han, hom_nay=None):
    return so_ngay_con_han(ngay_het_han, hom_nay) < SO_NGAY_CAN_HAN


def don_vi(thuoc):
    return thuoc.don_vi_tinh.ten_don_vi_tinh.lower()


def so(gia_tri):
    return f"{gia_tri:,}".replace(",", ".")
