from django.shortcuts import render

from ung_dung.chung.permissions import yeu_cau_vai_tro
from ung_dung.danh_muc.models import DonViTinh, NhomATC


@yeu_cau_vai_tro("quan_tri_chuoi")
def ban_do_nhiet(request):
    return render(
        request,
        "webgis/ban_do_nhiet.html",
        {"cac_nhom": NhomATC.objects.all(), "cac_don_vi": DonViTinh.objects.all()},
    )
