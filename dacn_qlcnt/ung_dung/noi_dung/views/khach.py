from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from ung_dung.chung.anh import tra_anh

from ..models import BannerTrangChu, TrangNoiDung


@require_GET
def trang(request, duong_dan):
    trang_nd = get_object_or_404(TrangNoiDung, duong_dan_trang=duong_dan, dang_hien_thi=True)
    return render(request, "noi_dung/khach/trang.html", {"trang_nd": trang_nd})


@require_GET
def anh_banner(request, ma):
    return tra_anh(request, get_object_or_404(BannerTrangChu, pk=ma))
