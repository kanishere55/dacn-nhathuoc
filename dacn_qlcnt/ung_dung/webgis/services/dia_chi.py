"""Tìm địa chỉ qua Nominatim (OpenStreetMap) từ máy chủ.

Làm đúng chính sách sử dụng của Nominatim: User-Agent định danh ứng dụng, tối đa
một yêu cầu mỗi giây cho toàn tiến trình, chỉ gọi khi người dùng bấm tìm, kết quả đã tìm được
giữ một ngày trong bộ nhớ đệm để không hỏi lại cùng một địa chỉ.
https://operations.osmfoundation.org/policies/nominatim/
"""

import hashlib
import json
import threading
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError

_khoa = threading.Lock()
_lan_goi_cuoi = [0.0]


THOI_GIAN_NHO_DEM_GIAY = 86400


def _goi(duong_dan, tham_so):
    khoa_dem = (
        "nominatim:"
        + hashlib.sha256(f"{duong_dan}?{urlencode(sorted(tham_so.items()))}".encode()).hexdigest()
    )
    da_luu = cache.get(khoa_dem)
    if da_luu is not None:
        return da_luu
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
            du_lieu = json.load(phan_hoi)
    except (URLError, TimeoutError, ValueError) as loi:
        raise ValidationError("Chưa kết nối được dịch vụ tìm địa chỉ, hãy thử lại.") from loi
    cache.set(khoa_dem, du_lieu, THOI_GIAN_NHO_DEM_GIAY)
    return du_lieu


SO_LAN_THU_GAN_DUNG = 2
NOI_KHUNG_DO = 0.35  # nới khung quanh các chi nhánh, khoảng 35–40 km


def _vung_uu_tien():
    """Khung bao các chi nhánh đang hoạt động (kinh độ trái, vĩ độ trên, kinh độ phải, vĩ độ dưới).

    Nominatim chỉ dùng khung này để xếp kết quả trong vùng phục vụ lên trước (không loại kết quả
    ngoài khung). Chuỗi chưa có chi nhánh thì không gửi khung.
    """
    from ung_dung.danh_muc.models import ChiNhanh

    cac_diem = [
        cn.vi_tri
        for cn in ChiNhanh.objects.filter(dang_hoat_dong=True, vi_tri__isnull=False).only("vi_tri")
    ]
    if not cac_diem:
        return ""
    kinh_do = [d.x for d in cac_diem]
    vi_do = [d.y for d in cac_diem]
    return ",".join(
        f"{so:.4f}"
        for so in (
            min(kinh_do) - NOI_KHUNG_DO,
            max(vi_do) + NOI_KHUNG_DO,
            max(kinh_do) + NOI_KHUNG_DO,
            min(vi_do) - NOI_KHUNG_DO,
        )
    )


def _cac_cach_viet_gon(tu_khoa):
    """Các cách viết ngắn dần của một địa chỉ, dùng khi tìm nguyên văn không ra.

    Dữ liệu bản đồ ghi tên phường, xã hiện hành, trong khi người dùng hay gõ số nhà kèm tên
    phường cũ ("45 Lê Lợi, Bến Nghé"). Bỏ dần phần sau dấu phẩy cuối, rồi bỏ số nhà, thì vẫn
    tìm được con đường để người dùng kéo ghim tới đúng nhà.
    """
    cac_phan = [phan.strip() for phan in tu_khoa.split(",") if phan.strip()]
    da_co = {tu_khoa.strip().lower()}
    while len(cac_phan) > 1:
        cac_phan = cac_phan[:-1]
        ung_vien = ", ".join(cac_phan)
        if len(ung_vien) >= 3 and ung_vien.lower() not in da_co:
            da_co.add(ung_vien.lower())
            yield ung_vien
    dau, _, con_lai = (cac_phan[0] if cac_phan else "").partition(" ")
    if any(ky_tu.isdigit() for ky_tu in dau) and len(con_lai.strip()) >= 3:
        if con_lai.strip().lower() not in da_co:
            yield con_lai.strip()


def _tim(tu_khoa, vung):
    tham_so = {"q": tu_khoa, "format": "jsonv2", "countrycodes": "vn", "limit": 6}
    if vung:
        tham_so["viewbox"] = vung
    return [
        {"dia_chi": muc["display_name"], "vi_do": float(muc["lat"]), "kinh_do": float(muc["lon"])}
        for muc in _goi("search", tham_so)
    ]


def tim_dia_chi(tu_khoa):
    """Trả (danh sách kết quả, gần đúng hay không).

    Tìm nguyên văn trước. Không có kết quả thì thử tối đa SO_LAN_THU_GAN_DUNG cách viết gọn
    hơn; kết quả khi đó chỉ gần đúng (thường là con đường), nơi gọi phải nói rõ với người dùng.
    """
    vung = _vung_uu_tien()
    ket_qua = _tim(tu_khoa, vung)
    if ket_qua:
        return ket_qua, False
    for so, ung_vien in enumerate(_cac_cach_viet_gon(tu_khoa)):
        if so >= SO_LAN_THU_GAN_DUNG:
            break
        ket_qua = _tim(ung_vien, vung)
        if ket_qua:
            return ket_qua, True
    return [], False


def dia_chi_tu_toa_do(vi_do, kinh_do):
    ket_qua = _goi(
        "reverse",
        {"lat": f"{vi_do:.6f}", "lon": f"{kinh_do:.6f}", "format": "jsonv2", "zoom": 18},
    )
    return ket_qua.get("display_name", "")
