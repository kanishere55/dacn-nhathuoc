"""Quãng đường theo đường bộ (OSRM) từ vị trí của khách tới các chi nhánh, gọi từ máy chủ.

Dịch vụ OSRM (http://project-osrm.org) trả ma trận khoảng cách theo mạng đường OpenStreetMap.
PostGIS (ST_DWithin, ST_Distance) lọc và sắp sơ bộ chi nhánh; OSRM cho quãng đường đi thực tế để
hiển thị và chọn chi nhánh gần nhất. Khi OSRM không phản hồi, hệ thống ước tính bằng khoảng cách
địa lý nhân hệ số 1,4 (đường đi trong đô thị thường dài hơn khoảng cách thẳng) và đánh dấu ước tính.
"""

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

HE_SO_UOC_TINH = 1.4
# ---------------------------------------------------------------- Quãng đường từ vị trí của khách
# Tốc độ xe máy trung bình trong đô thị; trùng hằng số TOC_DO_XE_MAY_KM_GIO trong nen_ban_do.js.
TOC_DO_XE_MAY_KM_GIO = 28
THOI_GIAN_NHO_DEM_GIAY = 600


def _goi_osrm_tu_vi_tri(vi_tri, cac_diem_den):
    """Bảng OSRM một nguồn (vị trí khách) tới nhiều đích (chi nhánh): danh sách mét theo đường bộ."""
    if not settings.OSRM_BASE_URL:
        raise ValueError("chua_cau_hinh_osrm")
    toa_do = ";".join(f"{p.x:.6f},{p.y:.6f}" for p in (vi_tri, *cac_diem_den))
    dich = ";".join(str(so) for so in range(1, len(cac_diem_den) + 1))
    yeu_cau = Request(
        f"{settings.OSRM_BASE_URL}/table/v1/driving/{toa_do}"
        f"?sources=0&destinations={dich}&annotations=distance",
        headers={"User-Agent": settings.HTTP_USER_AGENT},
    )
    with urlopen(yeu_cau, timeout=6) as phan_hoi:
        du_lieu = json.load(phan_hoi)
    if du_lieu.get("code") != "Ok":
        raise ValueError(du_lieu.get("code"))
    return du_lieu["distances"][0]


def quang_duong_tu_vi_tri(vi_tri, cac_diem):
    """Quãng đường đi thực tế từ vị trí của khách tới từng chi nhánh, một lần gọi OSRM.

    `cac_diem`: danh sách (khóa, Point chi nhánh, khoảng cách PostGIS tính bằng mét).
    Trả {khóa: {"quang_duong_met", "phut_xe_may", "uoc_tinh"}}. OSRM không phản hồi thì ước tính
    bằng khoảng cách PostGIS nhân HE_SO_UOC_TINH và đánh dấu `uoc_tinh`. Kết quả giữ 10 phút trong
    bộ nhớ đệm theo tọa độ làm tròn (~10 m) để trang đặt hàng đổi chi nhánh không phải gọi lại.
    """
    if not cac_diem:
        return {}
    khoa_dem = "quang_duong:{:.4f},{:.4f}:{}".format(
        vi_tri.y, vi_tri.x, ",".join(f"{p.x:.5f},{p.y:.5f}" for _, p, _ in cac_diem)
    )
    cac_met = cache.get(khoa_dem)
    if cac_met is None:
        try:
            cac_met = [
                round(met) if met is not None else None
                for met in _goi_osrm_tu_vi_tri(vi_tri, [p for _, p, _ in cac_diem])
            ]
            cache.set(khoa_dem, cac_met, THOI_GIAN_NHO_DEM_GIAY)
        except (URLError, TimeoutError, ValueError, KeyError, IndexError, OSError):
            cac_met = [None] * len(cac_diem)
    ket_qua = {}
    for (khoa, _, thang), met in zip(cac_diem, cac_met, strict=True):
        uoc_tinh = met is None
        met = round(thang * HE_SO_UOC_TINH) if uoc_tinh else met
        ket_qua[khoa] = {
            "quang_duong_met": met,
            "phut_xe_may": max(1, round(met / 1000 / TOC_DO_XE_MAY_KM_GIO * 60)),
            "uoc_tinh": uoc_tinh,
        }
    return ket_qua
