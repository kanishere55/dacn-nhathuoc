from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from ung_dung.chung.permissions import yeu_cau_vai_tro

from .forms import KichBanForm
from .selectors import lay_ket_qua_moi_nhat
from .services.kich_ban import tao_kich_ban


@yeu_cau_vai_tro("quan_tri_chuoi")
@require_http_methods(["GET", "POST"])
def ket_qua(request):
    form = KichBanForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            tao_kich_ban(request.user, **form.cleaned_data)
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("du_bao:ket_qua")
    return render(request, "du_bao/ket_qua.html", {"form": form, **lay_ket_qua_moi_nhat()})
