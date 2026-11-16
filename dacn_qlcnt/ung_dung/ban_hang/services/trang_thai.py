"""Bảng chuyển trạng thái hợp lệ của đơn đặt giữ; mọi lần đổi đều ghi lich_su_don_hang."""

from django.core.exceptions import ValidationError

from ..models import TRANG_THAI_DON, LichSuDonHang

NHAN = dict(TRANG_THAI_DON)
KHACH, NHAN_SU, HE_THONG = "khach", "nhan_su", "he_thong"

# (từ, đến) -> những bên được thực hiện. Đơn đặt giữ chỉ có một trạng thái đang xử lý: khách
# đến quầy nhận và trả tiền (hoàn thành), tự hủy hoặc nhà thuốc hủy, hoặc quá hạn giữ.
CHUYEN_HOP_LE = {
    ("dang_giu", "hoan_thanh"): {NHAN_SU},
    ("dang_giu", "da_huy"): {KHACH, NHAN_SU},
    ("dang_giu", "het_han"): {HE_THONG, KHACH, NHAN_SU},
}


def ben_thuc_hien(nguoi):
    if nguoi is None:
        return HE_THONG
    return KHACH if nguoi.vai_tro == "khach_hang" else NHAN_SU


def kiem_tra_chuyen(don, den, nguoi):
    cac_ben = CHUYEN_HOP_LE.get((don.trang_thai, den))
    if not cac_ben or ben_thuc_hien(nguoi) not in cac_ben:
        raise ValidationError(
            f"Không thể chuyển đơn từ “{NHAN[don.trang_thai]}” sang “{NHAN[den]}”."
        )


def ghi_lich_su(don, tu, den, nguoi, ghi_chu=""):
    return LichSuDonHang.objects.create(
        don_hang=don, tu_trang_thai=tu, den_trang_thai=den, nguoi_thuc_hien=nguoi, ghi_chu=ghi_chu
    )


def doi_trang_thai(don, den, nguoi, ghi_chu="", *, them_cot=()):
    """Đơn phải được khóa sẵn bằng select_for_update trong transaction hiện tại."""
    kiem_tra_chuyen(don, den, nguoi)
    tu = don.trang_thai
    don.trang_thai = den
    don.save(update_fields=["trang_thai", *them_cot])
    ghi_lich_su(don, tu, den, nguoi, ghi_chu)
    return tu
