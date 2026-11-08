"""Phí giao và chọn chi nhánh giao hàng.

Biểu phí: 15.000 đ cho 3 km đầu, mỗi km tiếp theo (làm tròn lên) 5.000 đ. Chỉ giao
trong 15 km đường đi tính từ chi nhánh. Chi nhánh được đề xuất là chi nhánh còn đủ
hàng có quãng đường ngắn nhất; khách có thể chọn chi nhánh đủ điều kiện khác.
"""

import math
from decimal import Decimal

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D

from ung_dung.danh_muc.selectors import lay_chi_nhanh_cong_khai
from ung_dung.kho.selectors import loc_chi_nhanh_du_thuoc
from ung_dung.webgis.services.duong_di import khoang_cach_duong_di

PHI_CO_BAN = 15_000
MET_CO_BAN = 3_000
PHI_MOI_KM = 5_000
BAN_KINH_GIAO_MET = 15_000
SO_CHI_NHANH_XET = 4


def tinh_phi_giao(khoang_cach_met):
    if khoang_cach_met <= MET_CO_BAN:
        return Decimal(PHI_CO_BAN)
    so_km_them = math.ceil((khoang_cach_met - MET_CO_BAN) / 1000)
    return Decimal(PHI_CO_BAN + so_km_them * PHI_MOI_KM)


def phuong_an_giao(vi_tri, cac_dong):
    """Các chi nhánh đủ hàng giao được tới `vi_tri`, gần nhất trước.

    Mỗi phần tử: {"chi_nhanh", "khoang_cach_met", "la_uoc_tinh", "phi_giao_hang"}.
    """
    gan_nhat = (
        lay_chi_nhanh_cong_khai()
        .annotate(khoang_cach_thang=Distance("vi_tri", vi_tri))
        .filter(vi_tri__distance_lte=(vi_tri, D(m=BAN_KINH_GIAO_MET)))
        .order_by("khoang_cach_thang")
    )
    du_hang = loc_chi_nhanh_du_thuoc(list(gan_nhat), cac_dong)[:SO_CHI_NHANH_XET]
    cac_quang_duong = khoang_cach_duong_di(
        vi_tri, [cn.vi_tri for cn in du_hang], [cn.khoang_cach_thang.m for cn in du_hang]
    )
    ket_qua = [
        {
            "chi_nhanh": cn,
            "khoang_cach_met": met,
            "la_uoc_tinh": uoc_tinh,
            "phi_giao_hang": tinh_phi_giao(met),
        }
        for cn, (met, uoc_tinh) in zip(du_hang, cac_quang_duong, strict=True)
        if met <= BAN_KINH_GIAO_MET
    ]
    return sorted(ket_qua, key=lambda muc: muc["khoang_cach_met"])
