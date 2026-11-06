from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.views.decorators.vary import vary_on_headers

from ung_dung.chung.permissions import yeu_cau_vai_tro

from .forms import LocBaoCaoForm
from .selectors import lay_bao_cao


@yeu_cau_vai_tro("quan_ly_chi_nhanh")
@require_GET
@vary_on_headers("HX-Request")
def tong_hop(request):
    form = LocBaoCaoForm(request.GET or None, nguoi=request.user)
    tham_so = form.initial if not form.is_bound else form.cleaned_data if form.is_valid() else None
    bao_cao = lay_bao_cao(request.user, **tham_so) if tham_so is not None else None
    tep = "bao_cao/tong_hop.html"
    if request.headers.get("HX-Request"):
        tep += "#ket_qua"
    return render(request, tep, {"form": form, "bao_cao": bao_cao})
