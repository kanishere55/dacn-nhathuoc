from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from ung_dung.chung.permissions import yeu_cau_vai_tro
from ung_dung.danh_muc.selectors import lay_chi_nhanh_cong_khai

from ..forms import MoPhongForm
from ..selectors import lay_cac_phong, lay_lich_su
from ..services import mo_phong


@yeu_cau_vai_tro("khach_hang")
@require_http_methods(["GET", "POST"])
def danh_sach(request):
    ma = request.GET.get("chi_nhanh", "")[:32]
    chi_nhanh = lay_chi_nhanh_cong_khai().filter(ma_chi_nhanh=ma).first() if ma else None
    form = MoPhongForm(
        request.POST if request.method == "POST" else None, initial={"chi_nhanh": chi_nhanh}
    )
    if form.is_bound and form.is_valid():
        try:
            phong = mo_phong(request.user, form.cleaned_data["chi_nhanh"])
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("tro_chuyen:khach_chi_tiet", ma=phong.pk)
    return render(
        request,
        "tro_chuyen/khach/danh_sach.html",
        {"cac_phong": lay_cac_phong(request.user), "form": form},
    )


@yeu_cau_vai_tro("khach_hang")
@require_GET
def chi_tiet(request, ma):
    phong = get_object_or_404(lay_cac_phong(request.user), pk=ma)
    return render(
        request,
        "tro_chuyen/khach/chi_tiet.html",
        {"phong": phong, "cac_tin": lay_lich_su(request.user, phong)},
    )
