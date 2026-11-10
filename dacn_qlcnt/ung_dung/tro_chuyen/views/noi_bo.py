from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from ung_dung.chung.permissions import yeu_cau_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from ..selectors import lay_cac_phong, lay_hop_thu, lay_lich_su


@yeu_cau_quyen("tro_chuyen.dung")
@require_GET
def danh_sach(request):
    return render(
        request,
        "tro_chuyen/danh_sach.html",
        {
            "cac_phong": lay_hop_thu(request.user),
            "nhieu_chi_nhanh": lay_chi_nhanh(request.user).count() > 1,
        },
    )


@yeu_cau_quyen("tro_chuyen.dung")
@require_GET
def chi_tiet(request, ma):
    phong = get_object_or_404(lay_cac_phong(request.user), pk=ma)
    return render(
        request,
        "tro_chuyen/chi_tiet.html",
        {"phong": phong, "cac_tin": lay_lich_su(request.user, phong)},
    )
