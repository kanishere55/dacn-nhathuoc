from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from ung_dung.chung.anh import tra_anh

from ..models import BannerTrangChu, TrangNoiDung
from ..selectors import nguon_hinh_anh_cong_khai, tin_tuc_cong_khai


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


@require_GET
def nguon_hinh_anh(request):
    """Ghi công tác giả và giấy phép của ảnh đang hiện trên website (CC BY-SA bắt buộc ghi công).

    Thông tin nằm ở một trang riêng thay vì dưới từng ảnh sản phẩm (Q39)."""
    return render(
        request, "noi_dung/khach/nguon_hinh_anh.html", {"nhom_anh": nguon_hinh_anh_cong_khai()}
    )
