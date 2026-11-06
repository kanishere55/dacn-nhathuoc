from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.vary import vary_on_headers

from ung_dung.chung.permissions import la_quan_tri

from ..forms import NHAN, lay_form
from ..selectors import DANH_MUC, lay_danh_muc
from ..services.danh_muc import luu_danh_muc


@vary_on_headers("HX-Request")
def hien_danh_sach(request, loai):
    danh_sach = Paginator(lay_danh_muc(request.user, loai, request.GET.get("q", "")), 25).get_page(
        request.GET.get("page")
    )
    cac_cot = DANH_MUC[loai][2]
    cac_dong = [
        (doi_tuong.pk, [getattr(doi_tuong, cot) for cot in cac_cot]) for doi_tuong in danh_sach
    ]
    return render(
        request,
        "danh_muc/_bang.html" if request.headers.get("HX-Request") else "danh_muc/danh_sach.html",
        {
            "tieu_de": DANH_MUC[loai][1],
            "loai": loai,
            "cac_cot": [NHAN.get(cot, cot) for cot in cac_cot],
            "cac_dong": cac_dong,
            "trang": danh_sach,
            "duoc_sua": la_quan_tri(request.user),
        },
    )


def hien_form(request, loai, ma=None):
    doi_tuong = get_object_or_404(lay_danh_muc(request.user, loai), pk=ma) if ma else None
    form = lay_form(loai)(request.POST or None, instance=doi_tuong)
    if request.method == "POST" and form.is_valid():
        try:
            luu_danh_muc(request.user, loai, form.cleaned_data, doi_tuong)
        except ValidationError as loi:
            form.add_error(None, loi)
        except IntegrityError:
            form.add_error(None, "Mã trùng hoặc dữ liệu đã được thay đổi.")
        else:
            return redirect(f"danh_muc:{loai}_danh_sach")
    return render(request, "danh_muc/form.html", {"form": form, "tieu_de": DANH_MUC[loai][1]})
