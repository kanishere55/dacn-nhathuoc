from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import NHAN_SU_CHI_NHANH, NHAN_SU_CHUOI, co_vai_tro, yeu_cau_vai_tro

from ..forms import DongNhapFormSet, PhieuNhapForm
from ..models import PhieuNhap
from ..selectors import lay_phieu
from ..services.phieu_nhap import nhap_hang
from . import chung_tu


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def danh_sach(request):
    return render(
        request,
        "kho/danh_sach_phieu.html",
        {
            "tieu_de": "Phiếu nhập",
            "cac_phieu": lay_phieu(request.user, PhieuNhap),
            "url_tao": (
                "kho:phieu_nhap_tao" if co_vai_tro(request.user, *NHAN_SU_CHI_NHANH) else None
            ),
            "url_chi_tiet": "kho:phieu_nhap_chi_tiet",
        },
    )


@yeu_cau_vai_tro(*NHAN_SU_CHI_NHANH)
def tao(request):
    form = PhieuNhapForm(request.POST or None, nguoi=request.user)
    cac_dong = DongNhapFormSet(request.POST or None)
    if request.method == "POST" and form.is_valid() and cac_dong.is_valid():
        try:
            phieu = nhap_hang(
                request.user,
                form.cleaned_data["chi_nhanh"],
                form.cleaned_data["nha_cung_cap"],
                [dong for dong in cac_dong.cleaned_data if dong and not dong.get("DELETE")],
                form.cleaned_data["ghi_chu"],
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("kho:phieu_nhap_chi_tiet", ma=phieu.pk)
    return render(
        request, "kho/form_phieu.html", {"form": form, "cac_dong": cac_dong, "tieu_de": "Nhập hàng"}
    )


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def chi_tiet(request, ma):
    return chung_tu.hien_thi(request, get_object_or_404(lay_phieu(request.user, PhieuNhap), pk=ma))


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def pdf(request, ma):
    return chung_tu.tra_pdf(request, get_object_or_404(lay_phieu(request.user, PhieuNhap), pk=ma))
