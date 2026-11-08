from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import co_vai_tro, yeu_cau_vai_tro

from ..forms import DongTraFormSet, PhieuTraForm
from ..models import ChiTietPhieuTraNhaCungCap, PhieuTraNhaCungCap
from ..selectors import lay_phieu
from ..services.phieu_tra_nha_cung_cap import tra_nha_cung_cap


@yeu_cau_vai_tro("quan_tri_chuoi", "quan_ly_chi_nhanh")
def danh_sach(request):
    return render(
        request,
        "kho/danh_sach_phieu.html",
        {
            "tieu_de": "Trả nhà cung cấp",
            "cac_phieu": lay_phieu(request.user, PhieuTraNhaCungCap, "phieu_nhap__chi_nhanh"),
            "url_tao": (
                "kho:phieu_tra_tao" if co_vai_tro(request.user, "quan_ly_chi_nhanh") else None
            ),
            "url_chi_tiet": "kho:phieu_tra_chi_tiet",
        },
    )


@yeu_cau_vai_tro("quan_ly_chi_nhanh")
def tao(request):
    form = PhieuTraForm(request.POST or None, nguoi=request.user)
    cac_dong = DongTraFormSet(request.POST or None, form_kwargs={"nguoi": request.user})
    if request.method == "POST" and form.is_valid() and cac_dong.is_valid():
        try:
            phieu = tra_nha_cung_cap(
                request.user,
                form.cleaned_data["phieu_nhap"],
                [d for d in cac_dong.cleaned_data if d and not d.get("DELETE")],
                form.cleaned_data["ghi_chu"],
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("kho:phieu_tra_chi_tiet", ma=phieu.pk)
    return render(
        request,
        "kho/form_phieu.html",
        {"form": form, "cac_dong": cac_dong, "tieu_de": "Trả nhà cung cấp"},
    )


@yeu_cau_vai_tro("quan_tri_chuoi", "quan_ly_chi_nhanh")
def chi_tiet(request, ma):
    phieu = get_object_or_404(
        lay_phieu(request.user, PhieuTraNhaCungCap, "phieu_nhap__chi_nhanh"), pk=ma
    )
    return render(
        request,
        "kho/chi_tiet_phieu.html",
        {
            "phieu": phieu,
            "tieu_de": phieu.ma_phieu_tra_nha_cung_cap,
            "cac_dong": ChiTietPhieuTraNhaCungCap.objects.filter(
                phieu_tra_nha_cung_cap=phieu
            ).select_related("lo_thuoc__thuoc"),
        },
    )
