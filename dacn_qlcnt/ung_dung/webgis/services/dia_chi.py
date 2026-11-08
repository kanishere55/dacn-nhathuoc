"""Tìm địa chỉ qua Nominatim (OpenStreetMap) từ máy chủ.

Làm đúng chính sách sử dụng của Nominatim: User-Agent định danh ứng dụng, tối đa
một yêu cầu mỗi giây cho toàn tiến trình, chỉ gọi khi người dùng bấm tìm.
https://operations.osmfoundation.org/policies/nominatim/
"""

import json
import threading
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError

_khoa = threading.Lock()
_lan_goi_cuoi = [0.0]


def _goi(duong_dan, tham_so):
    with _khoa:
        cho = 1.0 - (time.monotonic() - _lan_goi_cuoi[0])
        if cho > 0:
            time.sleep(cho)
        _lan_goi_cuoi[0] = time.monotonic()
    if settings.EMAIL_HOST_USER:
        tham_so = {**tham_so, "email": settings.EMAIL_HOST_USER}
    yeu_cau = Request(
        f"{settings.NOMINATIM_BASE_URL}/{duong_dan}?{urlencode(tham_so)}",
        headers={"User-Agent": settings.HTTP_USER_AGENT, "Accept-Language": "vi"},
    )
    try:
        with urlopen(yeu_cau, timeout=8) as phan_hoi:
            return json.load(phan_hoi)
    except (URLError, TimeoutError, ValueError) as loi:
        raise ValidationError("Chưa kết nối được dịch vụ tìm địa chỉ, hãy thử lại.") from loi


def tim_dia_chi(tu_khoa):
    ket_qua = _goi(
        "search",
        {"q": tu_khoa, "format": "jsonv2", "countrycodes": "vn", "limit": 6},
    )
    return [
        {"dia_chi": muc["display_name"], "vi_do": float(muc["lat"]), "kinh_do": float(muc["lon"])}
        for muc in ket_qua
    ]


def dia_chi_tu_toa_do(vi_do, kinh_do):
    ket_qua = _goi(
        "reverse",
        {"lat": f"{vi_do:.6f}", "lon": f"{kinh_do:.6f}", "format": "jsonv2", "zoom": 18},
    )
    return ket_qua.get("display_name", "")
