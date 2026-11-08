from django.conf import settings
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from ung_dung.chung.permissions import co_vai_tro
from ung_dung.danh_muc.selectors import lay_thuoc_cong_khai


@ensure_csrf_cookie
def ban_do(request):
    return render(
        request,
        "webgis/khach/ban_do.html",
        {
            "cac_thuoc": lay_thuoc_cong_khai(),
            "may_chu_osrm": getattr(settings, "OSRM_BASE_URL", "https://router.project-osrm.org"),
            "duoc_dat_giu": co_vai_tro(request.user, "khach_hang"),
        },
    )
