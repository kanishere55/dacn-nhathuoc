from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import co_vai_tro, yeu_cau_vai_tro

from ..forms import DongThuocFormSet, PhieuDieuChuyenForm
from ..models import PhieuDieuChuyen
from ..selectors import lay_phieu
from ..services.phieu_dieu_chuyen import dieu_chuyen
from . import chung_tu


@yeu_cau_vai_tro("quan_tri_chuoi", "quan_ly_chi_nhanh")
def danh_sach(request):
    return render(
        request,
        "kho/danh_sach_phieu.html",
        {
            "tieu_de": "Điều chuyển",
            "cac_phieu": lay_phieu(request.user, PhieuDieuChuyen, "chi_nhanh_nguon"),
            "url_tao": (
                "kho:phieu_dieu_chuyen_tao"
                if co_vai_tro(request.user, "quan_ly_chi_nhanh")
                else None
            ),
            "url_chi_tiet": "kho:phieu_dieu_chuyen_chi_tiet",
        },
    )


@yeu_cau_vai_tro("quan_ly_chi_nhanh")
def tao(request):
    form = PhieuDieuChuyenForm(request.POST or None, nguoi=request.user)
    cac_dong = DongThuocFormSet(request.POST or None)
    if request.method == "POST" and form.is_valid() and cac_dong.is_valid():
        try:
            phieu = dieu_chuyen(
                request.user,
                form.cleaned_data["chi_nhanh_nguon"],
                form.cleaned_data["chi_nhanh_dich"],
                [d for d in cac_dong.cleaned_data if d and not d.get("DELETE")],
                form.cleaned_data["ghi_chu"],
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("kho:phieu_dieu_chuyen_chi_tiet", ma=phieu.pk)
    return render(
        request,
        "kho/form_phieu.html",
        {"form": form, "cac_dong": cac_dong, "tieu_de": "Điều chuyển hai chi nhánh"},
    )


def _phieu(request, ma):
    return get_object_or_404(lay_phieu(request.user, PhieuDieuChuyen, "chi_nhanh_nguon"), pk=ma)


@yeu_cau_vai_tro("quan_tri_chuoi", "quan_ly_chi_nhanh")
def chi_tiet(request, ma):
    return chung_tu.hien_thi(request, _phieu(request, ma))


@yeu_cau_vai_tro("quan_tri_chuoi", "quan_ly_chi_nhanh")
def pdf(request, ma):
    return chung_tu.tra_pdf(request, _phieu(request, ma))
