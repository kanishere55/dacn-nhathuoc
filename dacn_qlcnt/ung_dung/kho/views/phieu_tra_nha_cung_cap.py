from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen

from ..forms import DongTraFormSet, PhieuTraForm
from ..models import PhieuTraNhaCungCap
from ..selectors import lay_phieu
from ..services.phieu_tra_nha_cung_cap import tra_nha_cung_cap
from . import chung_tu


@yeu_cau_quyen("phieu_tra.xem")
def danh_sach(request):
    return chung_tu.hien_danh_sach(
        request,
        PhieuTraNhaCungCap,
        lay_phieu(request.user, PhieuTraNhaCungCap, "phieu_nhap__chi_nhanh"),
        tieu_de="Trả nhà cung cấp",
        url_tao="kho:phieu_tra_tao" if co_quyen(request.user, "phieu_tra.tao") else None,
        url_chi_tiet="kho:phieu_tra_chi_tiet",
        chi_nhanh="phieu_nhap__chi_nhanh",
    )


@yeu_cau_quyen("phieu_tra.tao")
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
        {
            "form": form,
            "cac_dong": cac_dong,
            "tieu_de": "Trả hàng cho nhà cung cấp",
            "mo_ta": "Trả lại hàng lỗi hoặc giao sai theo đúng phiếu nhập gốc. Chỉ trả được lô thuộc phiếu đó.",
            "nhan_dong": "Lô cần trả",
            "nhan_xac_nhan": "Lưu phiếu trả",
            "url_danh_sach": "kho:phieu_tra_danh_sach",
        },
    )


def _phieu(request, ma):
    return get_object_or_404(
        lay_phieu(request.user, PhieuTraNhaCungCap, "phieu_nhap__chi_nhanh"), pk=ma
    )


@yeu_cau_quyen("phieu_tra.xem")
def chi_tiet(request, ma):
    return chung_tu.hien_thi(request, _phieu(request, ma))


@yeu_cau_quyen("phieu_tra.xem")
def pdf(request, ma):
    return chung_tu.tra_pdf(request, _phieu(request, ma))
