from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from ung_dung.chung.permissions import NHAN_SU_CHI_NHANH, yeu_cau_vai_tro

from ..selectors import lay_cac_phong, lay_lich_su


@yeu_cau_vai_tro(*NHAN_SU_CHI_NHANH)
@require_GET
def danh_sach(request):
    return render(
        request,
        "tro_chuyen/danh_sach.html",
        {"cac_phong": lay_cac_phong(request.user)},
    )


@yeu_cau_vai_tro(*NHAN_SU_CHI_NHANH)
@require_GET
def chi_tiet(request, ma):
    phong = get_object_or_404(lay_cac_phong(request.user), pk=ma)
    return render(
        request,
        "tro_chuyen/chi_tiet.html",
        {"phong": phong, "cac_tin": lay_lich_su(request.user, phong)},
    )
