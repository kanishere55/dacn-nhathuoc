from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from ung_dung.ban_hang.forms import ThemThuocVaoGioForm
from ung_dung.chung.van_ban import cat_khoang_trang

from ..selectors import lay_chi_nhanh_cong_khai, lay_nhom_thuoc_cong_khai, lay_thuoc_cong_khai


@require_GET
def danh_sach_thuoc(request):
    tu_khoa = cat_khoang_trang(request.GET.get("q", ""))[:150]
    ma_nhom = request.GET.get("nhom", "")[:32]
    cac_thuoc = lay_thuoc_cong_khai(tu_khoa, ma_nhom)
    return render(
        request,
        "danh_muc/khach/danh_sach_thuoc.html",
        {
            "trang": Paginator(cac_thuoc, 12).get_page(request.GET.get("page")),
            "tu_khoa": tu_khoa,
            "ma_nhom": ma_nhom,
            "cac_nhom": lay_nhom_thuoc_cong_khai(),
        },
    )


@require_GET
def chi_tiet_thuoc(request, ma):
    thuoc = get_object_or_404(lay_thuoc_cong_khai(), ma_thuoc=ma)
    return render(
        request,
        "danh_muc/khach/chi_tiet_thuoc.html",
        {"thuoc": thuoc, "form_them": ThemThuocVaoGioForm(initial={"so_luong": 1})},
    )


@require_GET
def chi_tiet_chi_nhanh(request, ma):
    chi_nhanh = get_object_or_404(lay_chi_nhanh_cong_khai(), ma_chi_nhanh=ma)
    return render(request, "danh_muc/khach/chi_tiet_chi_nhanh.html", {"chi_nhanh": chi_nhanh})
