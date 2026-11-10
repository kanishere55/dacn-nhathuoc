from django.shortcuts import render

from ung_dung.chung.permissions import yeu_cau_quyen

from ..loc import loc_ton_kho
from ..selectors import lay_bang_ton, lay_canh_bao, lay_canh_bao_ton_thap


@yeu_cau_quyen("ton_kho.xem")
def danh_sach(request):
    return render(
        request, "kho/ton_kho.html", loc_ton_kho(request).ngu_canh(lay_bang_ton(request.user))
    )


@yeu_cau_quyen("ton_kho.xem")
def canh_bao(request):
    return render(
        request,
        "kho/canh_bao.html",
        {
            "cac_dong": lay_canh_bao(request.user),
            "cac_ton_thap": lay_canh_bao_ton_thap(request.user),
        },
    )
