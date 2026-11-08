from django.conf import settings
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from ung_dung.chung.permissions import co_vai_tro, yeu_cau_vai_tro
from ung_dung.danh_muc.models import DonViTinh, NhomATC, Thuoc


@ensure_csrf_cookie
def ban_do(request):
    return render(
        request,
        "webgis/ban_do.html",
        {
            "cac_thuoc": Thuoc.objects.filter(dang_hoat_dong=True)
            .select_related("don_vi_tinh")
            .order_by("ten_thuoc"),
            "may_chu_osrm": getattr(settings, "OSRM_BASE_URL", "https://router.project-osrm.org"),
            "duoc_dat_giu": co_vai_tro(request.user, "khach_hang"),
        },
    )


@yeu_cau_vai_tro("quan_tri_chuoi")
def ban_do_nhiet(request):
    return render(
        request,
        "webgis/ban_do_nhiet.html",
        {"cac_nhom": NhomATC.objects.all(), "cac_don_vi": DonViTinh.objects.all()},
    )
