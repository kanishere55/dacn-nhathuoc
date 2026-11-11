from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from ..du_lieu_form import du_lieu_thuoc, ton_ban_duoc_theo_thuoc
from ..forms import DongThuocFormSet, PhieuDieuChuyenForm
from ..loi_dong import cac_dong_da_nhap, gan_loi
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
        da_nhap = cac_dong_da_nhap(cac_dong)
        try:
            phieu = dieu_chuyen(
                request.user,
                form.cleaned_data["chi_nhanh_nguon"],
                form.cleaned_data["chi_nhanh_dich"],
                [du_lieu for _, du_lieu in da_nhap],
                form.cleaned_data["ghi_chu"],
                khoa_yeu_cau=form.cleaned_data["khoa_yeu_cau"],
            )
        except ValidationError as loi:
            gan_loi(form, [dong for dong, _ in da_nhap], loi)
        else:
            return redirect("kho:phieu_dieu_chuyen_chi_tiet", ma=phieu.pk)
    return render(
        request,
        "kho/form_phieu.html",
        {
            "form": form,
            "cac_dong": cac_dong,
            "tieu_de": "Điều chuyển hàng",
            "mo_ta": (
                "Chuyển thuốc sang chi nhánh khác. Hệ thống tự lấy lô gần hết hạn trước ở chi "
                "nhánh chuyển đi; chọn thuốc sẽ thấy lượng còn chuyển được."
            ),
            "nhan_dong": "Thuốc cần chuyển",
            "nhan_xac_nhan": "Chuyển hàng",
            "url_danh_sach": "kho:phieu_dieu_chuyen_danh_sach",
            "du_lieu_form": {
                "thuoc": du_lieu_thuoc(),
                "ton_thuoc": ton_ban_duoc_theo_thuoc(lay_chi_nhanh(request.user)),
                "o_chi_nhanh": "chi_nhanh_nguon",
            },
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
