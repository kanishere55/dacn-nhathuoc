from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import co_vai_tro, yeu_cau_vai_tro

from ..forms import DongXuatHuyFormSet, PhieuXuatHuyForm
from ..models import PhieuXuatHuy
from ..selectors import lay_lo_het_han_con_ton, lay_phieu
from ..services.phieu_xuat_huy import xuat_huy
from . import chung_tu


@yeu_cau_vai_tro("quan_tri_chuoi", "quan_ly_chi_nhanh")
def danh_sach(request):
    return render(
        request,
        "kho/danh_sach_phieu.html",
        {
            "tieu_de": "Xuất hủy",
            "cac_phieu": lay_phieu(request.user, PhieuXuatHuy).select_related(
                "chi_nhanh", "nguoi_lap"
            ),
            "url_tao": (
                "kho:phieu_xuat_huy_tao" if co_vai_tro(request.user, "quan_ly_chi_nhanh") else None
            ),
            "url_chi_tiet": "kho:phieu_xuat_huy_chi_tiet",
        },
    )


@yeu_cau_vai_tro("quan_ly_chi_nhanh")
def tao(request):
    ban_dau, ban_dau_dong = None, None
    if request.method == "GET" and request.GET.get("loai") == "het_han":
        # Lập sẵn mọi lô quá hạn còn tồn; quản lý vẫn xem lại và bấm xác nhận.
        cac_ton = lay_lo_het_han_con_ton(request.user.chi_nhanh)
        ban_dau = {"chi_nhanh": request.user.chi_nhanh, "loai_xuat_huy": "het_han"}
        ban_dau_dong = [{"lo_thuoc": t.lo_thuoc, "so_luong": t.kha_dung} for t in cac_ton[:50]]
        if not ban_dau_dong:
            messages.info(request, "Chi nhánh không có lô nào đã hết hạn còn tồn khả dụng.")
    form = PhieuXuatHuyForm(request.POST or None, initial=ban_dau, nguoi=request.user)
    cac_dong = DongXuatHuyFormSet(
        request.POST or None, initial=ban_dau_dong, form_kwargs={"nguoi": request.user}
    )
    if request.method == "POST" and form.is_valid() and cac_dong.is_valid():
        try:
            phieu = xuat_huy(
                request.user,
                form.cleaned_data["chi_nhanh"],
                form.cleaned_data["loai_xuat_huy"],
                [d for d in cac_dong.cleaned_data if d and not d.get("DELETE")],
                form.cleaned_data["ghi_chu"],
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("kho:phieu_xuat_huy_chi_tiet", ma=phieu.pk)
    return render(
        request,
        "kho/form_phieu.html",
        {
            "form": form,
            "cac_dong": cac_dong,
            "tieu_de": "Xuất hủy hàng hết hạn, hư hỏng",
            "url_lap_san": "kho:phieu_xuat_huy_tao",
        },
    )


def _phieu(request, ma):
    return get_object_or_404(lay_phieu(request.user, PhieuXuatHuy), pk=ma)


@yeu_cau_vai_tro("quan_tri_chuoi", "quan_ly_chi_nhanh")
def chi_tiet(request, ma):
    return chung_tu.hien_thi(request, _phieu(request, ma))


@yeu_cau_vai_tro("quan_tri_chuoi", "quan_ly_chi_nhanh")
def pdf(request, ma):
    return chung_tu.tra_pdf(request, _phieu(request, ma))
