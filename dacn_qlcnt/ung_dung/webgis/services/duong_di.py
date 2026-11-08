"""Quãng đường đi xe máy/ô tô theo OSRM, gọi từ máy chủ để phí giao không phụ thuộc trình duyệt.

Dịch vụ OSRM (http://project-osrm.org) trả ma trận khoảng cách theo mạng đường
OpenStreetMap. Khi OSRM không phản hồi, hệ thống ước tính bằng khoảng cách địa lý
nhân hệ số 1,4 (đường đi thực tế trong đô thị thường dài hơn đường chim bay) và
đánh dấu là ước tính.
"""

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

HE_SO_UOC_TINH = 1.4


def _goi_osrm(diem_den, cac_diem_di):
    toa_do = ";".join(f"{p.x:.6f},{p.y:.6f}" for p in (diem_den, *cac_diem_di))
    nguon = ";".join(str(so) for so in range(1, len(cac_diem_di) + 1))
    yeu_cau = Request(
        f"{settings.OSRM_BASE_URL}/table/v1/driving/{toa_do}"
        f"?sources={nguon}&destinations=0&annotations=distance",
        headers={"User-Agent": settings.HTTP_USER_AGENT},
    )
    with urlopen(yeu_cau, timeout=6) as phan_hoi:
        du_lieu = json.load(phan_hoi)
    if du_lieu.get("code") != "Ok":
        raise ValueError(du_lieu.get("code"))
    return [hang[0] for hang in du_lieu["distances"]]


def khoang_cach_duong_di(diem_den, cac_diem_di, cac_khoang_cach_thang):
    """Quãng đường từ từng điểm đi (chi nhánh) tới điểm đến (địa chỉ giao).

    Trả danh sách (mét, la_uoc_tinh) cùng thứ tự `cac_diem_di`.

    `cac_khoang_cach_thang` là khoảng cách địa lý PostGIS (mét) dùng khi phải ước tính.
    """
    if not cac_diem_di:
        return []
    try:
        ket_qua = _goi_osrm(diem_den, cac_diem_di)
    except (URLError, TimeoutError, ValueError, KeyError, IndexError, OSError):
        ket_qua = [None] * len(cac_diem_di)
    return [
        (round(met), False) if met is not None else (round(thang * HE_SO_UOC_TINH), True)
        for met, thang in zip(ket_qua, cac_khoang_cach_thang, strict=True)
    ]
