from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import co_vai_tro, yeu_cau_vai_tro
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from ..forms import DongKiemKeFormSet, PhieuKiemKeForm
from ..models import PhieuKiemKe
from ..selectors import lay_phieu, lay_so_du
from ..services.phieu_kiem_ke import kiem_ke
from . import chung_tu


@yeu_cau_vai_tro("quan_tri_chuoi", "quan_ly_chi_nhanh")
def danh_sach(request):
    return render(
        request,
        "kho/danh_sach_phieu.html",
        {
            "tieu_de": "Kiểm kê",
            "cac_phieu": lay_phieu(request.user, PhieuKiemKe),
            "url_tao": (
                "kho:phieu_kiem_ke_tao" if co_vai_tro(request.user, "quan_ly_chi_nhanh") else None
            ),
            "url_chi_tiet": "kho:phieu_kiem_ke_chi_tiet",
        },
    )


@yeu_cau_vai_tro("quan_ly_chi_nhanh")
def tao(request):
    cac_chi_nhanh = lay_chi_nhanh(request.user)
    ma = request.GET.get("chi_nhanh")
    chi_nhanh = (
        cac_chi_nhanh.filter(pk=ma).first() if ma and ma.isdecimal() else cac_chi_nhanh.first()
    )
    ban_dau = (
        [
            {"ton_kho": ton, "so_luong_so_sach": ton.so_luong}
            for ton in lay_so_du(nguoi=request.user, chi_nhanh=chi_nhanh)
        ]
        if chi_nhanh
        else []
    )
    form = PhieuKiemKeForm(
        request.POST or None, nguoi=request.user, initial={"chi_nhanh": chi_nhanh}
    )
    cac_dong = DongKiemKeFormSet(
        request.POST or None, initial=ban_dau, form_kwargs={"nguoi": request.user}
    )
    if request.method == "POST" and form.is_valid() and cac_dong.is_valid():
        try:
            phieu = kiem_ke(
                request.user,
                form.cleaned_data["chi_nhanh"],
                [d for d in cac_dong.cleaned_data if d and not d.get("DELETE")],
                form.cleaned_data["ghi_chu"],
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("kho:phieu_kiem_ke_chi_tiet", ma=phieu.pk)
    return render(
        request,
        "kho/form_phieu.html",
        {
            "form": form,
            "cac_dong": cac_dong,
            "tieu_de": "Kiểm kê",
            "cac_chi_nhanh": cac_chi_nhanh,
            "chi_nhanh_da_chon": chi_nhanh,
        },
    )


def _phieu(request, ma):
    return get_object_or_404(lay_phieu(request.user, PhieuKiemKe), pk=ma)


@yeu_cau_vai_tro("quan_tri_chuoi", "quan_ly_chi_nhanh")
def chi_tiet(request, ma):
    return chung_tu.hien_thi(request, _phieu(request, ma))


@yeu_cau_vai_tro("quan_tri_chuoi", "quan_ly_chi_nhanh")
def pdf(request, ma):
    return chung_tu.tra_pdf(request, _phieu(request, ma))
