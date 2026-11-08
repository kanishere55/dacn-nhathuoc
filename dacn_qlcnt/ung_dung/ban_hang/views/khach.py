from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from ung_dung.chung.permissions import yeu_cau_vai_tro

from ..selectors import lay_chi_tiet_don, lay_don
from ..services.dat_giu import huy_giu


@yeu_cau_vai_tro("khach_hang")
@require_GET
def danh_sach_don(request):
    return render(request, "ban_hang/khach/don_dat_giu.html", {"cac_don": lay_don(request.user)})


@yeu_cau_vai_tro("khach_hang")
@require_GET
def chi_tiet_don(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    return render(
        request,
        "ban_hang/khach/chi_tiet_dat_giu.html",
        {"don": don, "cac_dong": lay_chi_tiet_don(don)},
    )


@require_POST
@yeu_cau_vai_tro("khach_hang")
def huy_don(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    try:
        huy_giu(request.user, don)
    except ValidationError as loi:
        messages.error(request, ". ".join(loi.messages))
    return redirect("ban_hang:khach_don_dat_giu_chi_tiet", ma=don.pk)
