from django.shortcuts import render
from django.views.decorators.http import require_GET

from ung_dung.danh_muc.selectors import (
    lay_chi_nhanh_cong_khai,
    lay_danh_muc_san_pham_cong_khai,
    lay_thuoc_cong_khai,
)

from .permissions import NHAN_SU_CHUOI, yeu_cau_vai_tro
from .selectors import lay_bang_dieu_khien


@require_GET
def trang_chu(request):
    return render(
        request,
        "chung/khach/trang_chu.html",
        {
            "cac_danh_muc": lay_danh_muc_san_pham_cong_khai()[:8],
            "thuoc_giam_gia": lay_thuoc_cong_khai(dang_giam=True, sap_xep="giam_nhieu")[:4],
            "cac_thuoc": lay_thuoc_cong_khai()[:8],
            "cac_chi_nhanh": lay_chi_nhanh_cong_khai()[:3],
        },
    )


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
@require_GET
def bang_dieu_khien(request):
    return render(request, "chung/bang_dieu_khien.html", lay_bang_dieu_khien(request.user))
