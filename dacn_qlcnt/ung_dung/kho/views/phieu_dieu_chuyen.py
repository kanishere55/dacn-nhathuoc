from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen

from ..forms import DongThuocFormSet, PhieuDieuChuyenForm
from ..models import PhieuDieuChuyen
from ..selectors import lay_phieu_dieu_chuyen
from ..services.phieu_dieu_chuyen import dieu_chuyen
from . import chung_tu


@yeu_cau_quyen("dieu_chuyen.xem")
def danh_sach(request):
    return chung_tu.hien_danh_sach(
        request,
        PhieuDieuChuyen,
        lay_phieu_dieu_chuyen(request.user),
        tieu_de="Điều chuyển",
        url_tao="kho:phieu_dieu_chuyen_tao" if co_quyen(request.user, "dieu_chuyen.tao") else None,
        url_chi_tiet="kho:phieu_dieu_chuyen_chi_tiet",
        chi_nhanh="chi_nhanh_nguon",
    )


@yeu_cau_quyen("dieu_chuyen.tao")
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
        {
            "form": form,
            "cac_dong": cac_dong,
            "tieu_de": "Điều chuyển hàng",
            "mo_ta": "Chuyển thuốc sang chi nhánh khác. Hệ thống tự lấy lô gần hết hạn trước ở chi nhánh chuyển đi.",
            "nhan_dong": "Thuốc cần chuyển",
            "nhan_xac_nhan": "Chuyển hàng",
            "url_danh_sach": "kho:phieu_dieu_chuyen_danh_sach",
        },
    )


def _phieu(request, ma):
    return get_object_or_404(lay_phieu_dieu_chuyen(request.user), pk=ma)


@yeu_cau_quyen("dieu_chuyen.xem")
def chi_tiet(request, ma):
    return chung_tu.hien_thi(request, _phieu(request, ma))


@yeu_cau_quyen("dieu_chuyen.xem")
def pdf(request, ma):
    return chung_tu.tra_pdf(request, _phieu(request, ma))
