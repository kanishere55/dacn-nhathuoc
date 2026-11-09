from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ung_dung.chung.permissions import NHAN_SU_CHI_NHANH, NHAN_SU_CHUOI, co_vai_tro, yeu_cau_vai_tro
from ung_dung.kho.forms import DongThuocFormSet

from ..forms import PhieuBanForm
from ..hoa_don import du_lieu_hoa_don, ten_tep_pdf, ve_pdf
from ..selectors import lay_phieu_ban
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
                don_thuoc=form.don_thuoc(),
                phuong_thuc_thanh_toan=form.cleaned_data["phuong_thuc_thanh_toan"],
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
            "tieu_de": "Bán tại quầy · giá đang áp dụng / đơn vị cơ sở",
        },
    )


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def chi_tiet(request, ma):
    phieu = get_object_or_404(lay_phieu_ban(request.user), pk=ma)
    return render(request, "ban_hang/phieu_ban.html", {"hd": du_lieu_hoa_don(phieu)})


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def hoa_don_in(request, ma):
    phieu = get_object_or_404(lay_phieu_ban(request.user), pk=ma)
    return render(
        request,
        "ban_hang/hoa_don/in.html",
        {
            "hd": du_lieu_hoa_don(phieu),
            "url_quay_lai": reverse("ban_hang:phieu_ban_chi_tiet", args=[phieu.pk]),
            "url_pdf": reverse("ban_hang:phieu_ban_pdf", args=[phieu.pk]),
        },
    )


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def hoa_don_pdf(request, ma):
    phieu = get_object_or_404(lay_phieu_ban(request.user), pk=ma)
    return tra_pdf(phieu, tai_ve="tai" in request.GET)


def tra_pdf(phieu, *, tai_ve):
    phan_hoi = HttpResponse(ve_pdf(du_lieu_hoa_don(phieu)), content_type="application/pdf")
    kieu = "attachment" if tai_ve else "inline"
    phan_hoi["Content-Disposition"] = f'{kieu}; filename="{ten_tep_pdf(phieu)}"'
    phan_hoi["Cache-Control"] = "private, no-store"
    return phan_hoi
