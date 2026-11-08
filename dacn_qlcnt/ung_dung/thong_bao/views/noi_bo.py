from django.core.paginator import Paginator
from django.shortcuts import render

from ung_dung.chung.permissions import yeu_cau_vai_tro

from ..models import LOAI_EMAIL, TRANG_THAI
from ..selectors import lay_nhat_ky_email


@yeu_cau_vai_tro("quan_tri_chuoi")
def nhat_ky_email(request):
    bo_loc = {
        "loai_email": request.GET.get("loai_email", ""),
        "trang_thai": request.GET.get("trang_thai", ""),
        "tim": request.GET.get("tim", "").strip()[:100],
    }
    trang = Paginator(lay_nhat_ky_email(request.user, **bo_loc), 30).get_page(
        request.GET.get("trang")
    )
    return render(
        request,
        "thong_bao/nhat_ky_email.html",
        {"trang": trang, "bo_loc": bo_loc, "cac_loai": LOAI_EMAIL, "cac_trang_thai": TRANG_THAI},
    )
