from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from ung_dung.chung.permissions import yeu_cau_vai_tro

from .forms import MoPhongForm
from .selectors import lay_cac_phong, lay_lich_su
from .services import mo_phong


@yeu_cau_vai_tro("khach_hang", "nhan_vien", "quan_ly_chi_nhanh")
@require_http_methods(["GET", "POST"])
def danh_sach(request):
    form = MoPhongForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            phong = mo_phong(request.user, form.cleaned_data["chi_nhanh"])
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("tro_chuyen:chi_tiet", ma=phong.pk)
    return render(
        request,
        "tro_chuyen/danh_sach.html",
        {"cac_phong": lay_cac_phong(request.user), "form": form},
    )


@yeu_cau_vai_tro("khach_hang", "nhan_vien", "quan_ly_chi_nhanh")
def chi_tiet(request, ma):
    phong = get_object_or_404(lay_cac_phong(request.user), pk=ma)
    return render(
        request,
        "tro_chuyen/chi_tiet.html",
        {"phong": phong, "cac_tin": lay_lich_su(request.user, phong)},
    )
