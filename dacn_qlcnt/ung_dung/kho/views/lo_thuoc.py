from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.chung.permissions import la_quan_tri, yeu_cau_vai_tro

from ..models import LoThuoc
from ..selectors import lay_cac_lo
from ..services.lo_thuoc import doi_dieu_kien_ban


@yeu_cau_vai_tro("quan_tri_chuoi", "quan_ly_chi_nhanh")
def danh_sach(request):
    return render(
        request,
        "kho/lo_thuoc.html",
        {"cac_lo": lay_cac_lo(request.user), "duoc_sua": la_quan_tri(request.user)},
    )


@yeu_cau_vai_tro("quan_tri_chuoi")
@require_POST
def doi_trang_thai(request, ma):
    lo = get_object_or_404(LoThuoc, pk=ma)
    doi_dieu_kien_ban(request.user, lo, request.POST.get("duoc_phep_ban") == "1")
    return redirect("kho:lo_thuoc_danh_sach")
