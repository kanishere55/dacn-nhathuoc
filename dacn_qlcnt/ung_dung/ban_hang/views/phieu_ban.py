from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import NHAN_SU_CHI_NHANH, NHAN_SU_CHUOI, co_vai_tro, yeu_cau_vai_tro
from ung_dung.kho.forms import DongThuocFormSet

from ..forms import PhieuBanForm
from ..selectors import chi_tiet_ban, lay_phieu_ban, tong_tien_ban
from ..services.phieu_ban import ban_tai_quay


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def danh_sach(request):
    return render(
        request,
        "kho/danh_sach_phieu.html",
        {
            "tieu_de": "Bán hàng tại quầy",
            "cac_phieu": lay_phieu_ban(request.user),
            "url_tao": (
                "ban_hang:phieu_ban_tao" if co_vai_tro(request.user, *NHAN_SU_CHI_NHANH) else None
            ),
            "url_chi_tiet": "ban_hang:phieu_ban_chi_tiet",
        },
    )


@yeu_cau_vai_tro(*NHAN_SU_CHI_NHANH)
def tao(request):
    form = PhieuBanForm(request.POST or None, nguoi=request.user)
    cac_dong = DongThuocFormSet(request.POST or None)
    if request.method == "POST" and form.is_valid() and cac_dong.is_valid():
        try:
            phieu = ban_tai_quay(
                request.user,
                form.cleaned_data["chi_nhanh"],
                [d for d in cac_dong.cleaned_data if d and not d.get("DELETE")],
                khoa_yeu_cau=form.cleaned_data["khoa_yeu_cau"],
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("ban_hang:phieu_ban_chi_tiet", ma=phieu.pk)
    return render(
        request,
        "kho/form_phieu.html",
        {
            "form": form,
            "cac_dong": cac_dong,
            "tieu_de": "Bán tại quầy · giá hiện tại / đơn vị cơ sở",
        },
    )


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def chi_tiet(request, ma):
    phieu = get_object_or_404(lay_phieu_ban(request.user), pk=ma)
    return render(
        request,
        "ban_hang/phieu_ban.html",
        {"phieu": phieu, "cac_dong": chi_tiet_ban(phieu), "tong_tien": tong_tien_ban(phieu)},
    )
