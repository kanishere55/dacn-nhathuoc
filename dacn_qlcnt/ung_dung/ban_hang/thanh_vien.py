"""Hạng thành viên theo chi tiêu 12 tháng gần nhất; ưu đãi chỉ áp cho thuốc không kê đơn."""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import F, Sum
from django.utils import timezone

# (tên hạng, chi tiêu tối thiểu trong 365 ngày, phần trăm ưu đãi)
CAC_HANG = (
    ("Thành viên", 0, 0),
    ("Đồng", 1_000_000, 2),
    ("Bạc", 3_000_000, 3),
    ("Vàng", 5_000_000, 4),
    ("Kim cương", 8_000_000, 5),
)


def chi_tieu_12_thang(khach):
    from ung_dung.thanh_toan.models import GiaoDichThanhToan

    from .models import DonHang

    tu = timezone.now() - timedelta(days=365)
    don = DonHang.objects.filter(khach_hang=khach, trang_thai="hoan_thanh", thoi_diem_tao__gte=tu)
    mua = don.aggregate(tong=Sum(F("tien_hang") - F("giam_gia_thanh_vien"), default=0))["tong"]
    hoan = GiaoDichThanhToan.objects.filter(
        don_hang__in=don, loai_giao_dich="hoan", trang_thai="thanh_cong"
    ).aggregate(tong=Sum("so_tien", default=0))["tong"]
    return max(Decimal(mua) - Decimal(hoan), Decimal(0))


def hang_cua(khach):
    chi_tieu = chi_tieu_12_thang(khach)
    vi_tri = max(i for i, (_, nguong, _) in enumerate(CAC_HANG) if chi_tieu >= nguong)
    ten, nguong, phan_tram = CAC_HANG[vi_tri]
    ket_qua = {"ten": ten, "phan_tram": phan_tram, "chi_tieu": chi_tieu, "hang_sau": None}
    if vi_tri + 1 < len(CAC_HANG):
        ten_sau, nguong_sau, phan_tram_sau = CAC_HANG[vi_tri + 1]
        ket_qua.update(
            hang_sau=ten_sau,
            phan_tram_sau=phan_tram_sau,
            con_thieu=nguong_sau - chi_tieu,
            tien_do=int(100 * (chi_tieu - nguong) / (nguong_sau - nguong)),
        )
    return ket_qua


def giam_thanh_vien(phan_tram, cac_dong):
    """`cac_dong`: các bộ (thuốc, số lượng, đơn giá); thuốc kê đơn không được ưu đãi."""
    co_so = sum(
        (
            Decimal(don_gia) * so_luong
            for thuoc, so_luong, don_gia in cac_dong
            if not thuoc.la_thuoc_ke_don
        ),
        Decimal(0),
    )
    return (co_so * phan_tram / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
