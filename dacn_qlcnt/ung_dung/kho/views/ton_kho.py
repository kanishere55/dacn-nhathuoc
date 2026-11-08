from django.shortcuts import render

from ung_dung.chung.permissions import NHAN_SU_CHUOI, yeu_cau_vai_tro

from ..selectors import lay_bang_ton, lay_canh_bao, lay_canh_bao_ton_thap


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def danh_sach(request):
    return render(request, "kho/ton_kho.html", {"cac_dong": lay_bang_ton(request.user)})


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def canh_bao(request):
    return render(
        request,
        "kho/canh_bao.html",
        {
            "cac_dong": lay_canh_bao(request.user),
            "cac_ton_thap": lay_canh_bao_ton_thap(request.user),
        },
    )
