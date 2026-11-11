from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen

from ..du_lieu_form import lo_cua_phieu_nhap
from ..forms import DongTraFormSet, PhieuTraForm
from ..loi_dong import cac_dong_da_nhap, gan_loi
from ..models import PhieuNhap, PhieuTraNhaCungCap
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
    phieu_nhap = form.cleaned_data["phieu_nhap"] if form.is_bound and form.is_valid() else None
    cac_dong = DongTraFormSet(
        request.POST or None, form_kwargs={"nguoi": request.user, "phieu_nhap": phieu_nhap}
    )
    if phieu_nhap and cac_dong.is_valid():
        da_nhap = cac_dong_da_nhap(cac_dong)
        try:
            phieu = tra_nha_cung_cap(
                request.user,
                phieu_nhap,
                [du_lieu for _, du_lieu in da_nhap],
                form.cleaned_data["ghi_chu"],
                khoa_yeu_cau=form.cleaned_data["khoa_yeu_cau"],
            )
        except ValidationError as loi:
            gan_loi(form, [dong for dong, _ in da_nhap], loi)
        else:
            return redirect("kho:phieu_tra_chi_tiet", ma=phieu.pk)
    elif form.is_bound:
        cac_dong.is_valid()  # hiện lỗi từng dòng cùng lúc với lỗi đầu phiếu
    return render(
        request,
        "kho/form_phieu.html",
        {
            "form": form,
            "cac_dong": cac_dong,
            "tieu_de": "Trả hàng cho nhà cung cấp",
            "mo_ta": (
                "Trả lại hàng lỗi hoặc giao sai theo đúng phiếu nhập gốc. Chọn phiếu nhập trước, "
                "danh sách lô chỉ gồm lô của phiếu đó kèm số còn trả được."
            ),
            "nhan_dong": "Lô cần trả",
            "nhan_xac_nhan": "Lưu phiếu trả",
            "url_danh_sach": "kho:phieu_tra_danh_sach",
            "du_lieu_form": {"url_lo_theo_phieu": reverse("kho:phieu_tra_lo_theo_phieu")},
        },
    )


@yeu_cau_quyen("phieu_tra.tao")
@require_GET
def lo_theo_phieu(request):
    """Các lô của một phiếu nhập kèm số còn trả được, để form trả lọc ô chọn lô."""
    ma = request.GET.get("phieu_nhap", "")
    if not (ma.isascii() and ma.isdecimal()):
        return JsonResponse({"lo": []})
    phieu_nhap = get_object_or_404(lay_phieu(request.user, PhieuNhap), pk=ma)
    return JsonResponse({"lo": lo_cua_phieu_nhap(phieu_nhap)})


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
