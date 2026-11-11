"""Hạng thành viên theo chi tiêu 12 tháng gần nhất; ưu đãi chỉ áp cho thuốc không kê đơn.

Chương trình khách hàng thường xuyên là một hình thức khuyến mại, mà thuốc kê đơn không được
khuyến mại (Nghị định 81/2018/NĐ-CP Điều 5, sửa đổi bởi Nghị định 239/2026/NĐ-CP). Vì vậy
cả mức chi tiêu tính hạng lẫn ưu đãi đều chỉ xét dòng thuốc không kê đơn.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone

# (tên hạng, chi tiêu tối thiểu trong 365 ngày, phần trăm ưu đãi)
CAC_HANG = (
    ("Thành viên", 0, 0),
    ("Đồng", 1_000_000, 2),
    ("Bạc", 3_000_000, 3),
    ("Vàng", 5_000_000, 4),
    ("Kim cương", 8_000_000, 5),
)


TIEN = DecimalField(max_digits=20, decimal_places=4)


def chi_tieu_12_thang(khach):
    """Tiền khách thực trả cho thuốc không kê đơn ở đơn hoàn thành trong 365 ngày, trừ hàng trả.

    Mỗi dòng tính theo giá sau khuyến mãi trừ phần ưu đãi thành viên phân bổ cho dòng; phần
    đã hoàn của các dòng đó (yêu cầu trả hàng đã hoàn tiền) được trừ theo tỷ lệ số lượng.
    """
    from .models import ChiTietDonHang, ChiTietTraHang

    tu = timezone.now() - timedelta(days=365)
    cac_dong = ChiTietDonHang.objects.filter(
        don_hang__khach_hang=khach,
        don_hang__trang_thai="hoan_thanh",
        don_hang__thoi_diem_tao__gte=tu,
        thuoc__la_thuoc_ke_don=False,
    )
    mua = cac_dong.aggregate(
        tong=Sum(
            ExpressionWrapper(F("so_luong") * F("don_gia") - F("giam_gia_phan_bo"), TIEN),
            default=0,
        )
    )["tong"]
    hoan = ChiTietTraHang.objects.filter(
        chi_tiet_don_hang__in=cac_dong, yeu_cau_tra_hang__trang_thai="da_hoan_tien"
    ).aggregate(
        tong=Sum(
            ExpressionWrapper(
                F("so_luong") * F("chi_tiet_don_hang__don_gia")
                - F("chi_tiet_don_hang__giam_gia_phan_bo")
                * F("so_luong")
                / F("chi_tiet_don_hang__so_luong"),
                TIEN,
            ),
            default=0,
        )
    )["tong"]
    return max(Decimal(mua) - Decimal(hoan), Decimal(0)).quantize(Decimal(1))


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


def phan_bo_giam(tong_giam, cac_dong):
    """Chia `tong_giam` cho các dòng không kê đơn theo tỷ lệ thành tiền; trả list cùng thứ tự.

    Số đồng còn dư sau khi làm tròn xuống được phân theo phần lẻ lớn nhất, để tổng khớp
    với giảm giá của đơn và giảm giá từng dòng không vượt thành tiền dòng đó.
    """
    tong_giam = Decimal(tong_giam)
    thanh_tien = [
        Decimal(0) if thuoc.la_thuoc_ke_don else Decimal(don_gia) * so_luong
        for thuoc, so_luong, don_gia in cac_dong
    ]
    co_so = sum(thanh_tien, Decimal(0))
    if not tong_giam or not co_so:
        return [Decimal(0)] * len(cac_dong)
    cac_phan = [divmod(tong_giam * tien, co_so) for tien in thanh_tien]
    phan_bo = [phan for phan, _ in cac_phan]
    thu_tu = sorted(range(len(cac_phan)), key=lambda i: cac_phan[i][1], reverse=True)
    for i in thu_tu[: int(tong_giam - sum(phan_bo))]:
        phan_bo[i] += 1
    return phan_bo
