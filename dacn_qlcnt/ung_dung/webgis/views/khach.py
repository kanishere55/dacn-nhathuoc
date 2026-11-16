from django.conf import settings
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from ung_dung.ban_hang.gio_hang import SO_LUONG_TOI_DA, SO_THUOC_TOI_DA
from ung_dung.ban_hang.selectors import gio_duoc_giu, lay_dong_gio, lay_gio
from ung_dung.chung.permissions import NHAN_SU_CHUOI, co_vai_tro
from ung_dung.danh_muc.selectors import lay_thuoc_cong_khai

from ..selectors import lay_chi_nhanh_ban_do


@require_GET
@ensure_csrf_cookie
def ban_do(request):
    cac_dong = []
    if request.GET.get("tu_gio") == "1" and not co_vai_tro(request.user, *NHAN_SU_CHUOI):
        cac_dong = lay_dong_gio(lay_gio(request.session))
    tu_gio = gio_duoc_giu(cac_dong)
    cac_thuoc = lay_thuoc_cong_khai()
    ma_thuoc = request.GET.get("thuoc")
    return render(
        request,
        "webgis/khach/ban_do.html",
        {
            "cac_thuoc": () if tu_gio else cac_thuoc,
            "thuoc_ban_dau": cac_thuoc.filter(ma_thuoc=ma_thuoc).first() if ma_thuoc else None,
            "cac_dong": cac_dong,
            "tu_gio": tu_gio,
            "gioi_han_so_luong": SO_LUONG_TOI_DA,
            "gioi_han_so_thuoc": SO_THUOC_TOI_DA,
            "may_chu_osrm": settings.OSRM_BASE_URL,
            "may_chu_osrm_di_bo": settings.OSRM_DI_BO_BASE_URL,
            "cac_chi_nhanh": lay_chi_nhanh_ban_do(),
            "che_do_thuoc": bool(tu_gio or ma_thuoc),
        },
    )
