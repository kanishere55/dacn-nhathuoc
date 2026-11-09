from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from ung_dung.chung.anh import tra_anh

from ..models import BannerTrangChu, TrangNoiDung
from ..selectors import tin_tuc_cong_khai


@require_GET
def trang(request, duong_dan):
    trang_nd = get_object_or_404(TrangNoiDung, duong_dan_trang=duong_dan, dang_hien_thi=True)
    return render(request, "noi_dung/khach/trang.html", {"trang_nd": trang_nd})


@require_GET
def anh_banner(request, ma):
    return tra_anh(request, get_object_or_404(BannerTrangChu, pk=ma))


@require_GET
def tin_tuc_danh_sach(request):
    trang_tin = Paginator(tin_tuc_cong_khai().defer("noi_dung_tin_tuc"), 10).get_page(
        request.GET.get("page")
    )
    return render(request, "noi_dung/khach/tin_tuc_danh_sach.html", {"trang_tin": trang_tin})


@require_GET
def tin_tuc_chi_tiet(request, duong_dan):
    tin = get_object_or_404(tin_tuc_cong_khai(), duong_dan_tin_tuc=duong_dan)
    tin_khac = tin_tuc_cong_khai().exclude(pk=tin.pk).defer("noi_dung_tin_tuc")[:3]
    return render(
        request, "noi_dung/khach/tin_tuc_chi_tiet.html", {"tin": tin, "tin_khac": tin_khac}
    )
