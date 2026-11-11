"""Ghi giao dịch thu/hoàn; không gọi service đơn hàng để tránh phụ thuộc vòng."""

from django.core.exceptions import ValidationError
from django.utils import timezone

from ung_dung.kho.services.giao_dich import ma_chung_tu

from ..models import GiaoDichThanhToan


def tao_cho(don_hang, phuong_thuc):
    """Giao dịch chờ cho đơn trả trước; tiền khớp tổng đơn lúc đặt."""
    return GiaoDichThanhToan.objects.create(
        ma_giao_dich_thanh_toan=ma_chung_tu("GD"),
        don_hang=don_hang,
        loai_giao_dich="thu",
        phuong_thuc=phuong_thuc,
        so_tien=don_hang.tong_thanh_toan,
    )


def ghi_ngay(
    *,
    loai,
    phuong_thuc,
    so_tien,
    don_hang=None,
    phieu_ban=None,
    nguoi=None,
    ma_tham_chieu=None,
    ghi_chu="",
):
    """Giao dịch đã hoàn tất ngay: tiền mặt, COD, chuyển khoản tại quầy, hoàn tiền."""
    if nguoi is None and (loai == "hoan" or phuong_thuc in ("tien_mat", "cod")):
        raise ValidationError("Cần nhân sự xác nhận đã thu hoặc hoàn tiền.")
    return GiaoDichThanhToan.objects.create(
        ma_giao_dich_thanh_toan=ma_chung_tu("GD"),
        don_hang=don_hang,
        phieu_ban=phieu_ban,
        loai_giao_dich=loai,
        phuong_thuc=phuong_thuc,
        so_tien=so_tien,
        trang_thai="thanh_cong",
        ma_tham_chieu=ma_tham_chieu or None,
        ghi_chu=ghi_chu,
        nguoi_xac_nhan=nguoi,
        thoi_diem_hoan_tat=timezone.now(),
    )


def ket_thuc_cho(don_hang, trang_thai):
    """Đóng các giao dịch chờ của đơn khi đơn bị hủy hoặc quá hạn."""
    GiaoDichThanhToan.objects.filter(don_hang=don_hang, trang_thai="cho").update(
        trang_thai=trang_thai, thoi_diem_hoan_tat=timezone.now()
    )
