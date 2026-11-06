from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.chung.permissions import yeu_cau_vai_tro

from ..selectors import lay_chi_tiet_don, lay_don
from ..services.dat_giu import huy_giu
from ..services.phieu_ban import ban_tai_quay


@yeu_cau_vai_tro("khach_hang", "nhan_vien", "quan_ly_chi_nhanh")
def danh_sach(request):
    return render(request, "ban_hang/don_dat_giu.html", {"cac_don": lay_don(request.user)})


@yeu_cau_vai_tro("khach_hang", "nhan_vien", "quan_ly_chi_nhanh")
def chi_tiet(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    return render(
        request,
        "ban_hang/chi_tiet_dat_giu.html",
        {"don": don, "cac_dong": lay_chi_tiet_don(don)},
    )


@require_POST
@yeu_cau_vai_tro("khach_hang", "nhan_vien", "quan_ly_chi_nhanh")
def huy(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    try:
        huy_giu(request.user, don)
    except ValidationError as loi:
        messages.error(request, "; ".join(loi.messages))
    return redirect("ban_hang:don_dat_giu_chi_tiet", ma=ma)


@require_POST
@yeu_cau_vai_tro("nhan_vien", "quan_ly_chi_nhanh")
def nhan(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    try:
        phieu = ban_tai_quay(request.user, don.chi_nhanh, [], don_dat_giu=don)
    except ValidationError as loi:
        messages.error(request, "; ".join(loi.messages))
        return redirect("ban_hang:don_dat_giu_chi_tiet", ma=ma)
    return redirect("ban_hang:phieu_ban_chi_tiet", ma=phieu.pk)
