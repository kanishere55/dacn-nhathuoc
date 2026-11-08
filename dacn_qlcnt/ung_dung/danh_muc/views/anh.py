from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST

from ung_dung.chung.anh import tra_anh
from ung_dung.chung.permissions import yeu_cau_vai_tro

from ..forms import TaiAnhForm
from ..models import AnhChiNhanh, AnhThuoc
from ..selectors import CO_ANH
from ..services import anh as dich_vu


@require_GET
def anh_thuoc(request, ma):
    return tra_anh(request, get_object_or_404(AnhThuoc, pk=ma, thuoc__dang_hoat_dong=True))


@require_GET
def anh_chi_nhanh(request, ma):
    return tra_anh(request, get_object_or_404(AnhChiNhanh, pk=ma, chi_nhanh__dang_hoat_dong=True))


def _ve_trang_sua(loai, ma):
    return redirect(f"danh_muc:{loai}_sua", ma=ma)


@yeu_cau_vai_tro("quan_tri_chuoi")
@require_POST
def tai_len(request, loai, ma):
    doi_tuong = get_object_or_404(CO_ANH[loai][0], pk=ma)
    form = TaiAnhForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            so_anh = len(
                dich_vu.them_anh(request.user, loai, doi_tuong, form.cleaned_data["cac_anh"])
            )
        except ValidationError as loi:
            messages.error(request, " ".join(loi.messages))
        else:
            messages.success(request, f"Đã thêm {so_anh} ảnh.")
    else:
        messages.error(request, " ".join(form.errors.get("cac_anh", ["Ảnh không hợp lệ."])))
    return _ve_trang_sua(loai, ma)


@yeu_cau_vai_tro("quan_tri_chuoi")
@require_POST
def xoa(request, loai, ma, id_anh):
    doi_tuong = get_object_or_404(CO_ANH[loai][0], pk=ma)
    try:
        dich_vu.xoa_anh(request.user, loai, doi_tuong, id_anh)
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    else:
        messages.success(request, "Đã xóa ảnh.")
    return _ve_trang_sua(loai, ma)


@yeu_cau_vai_tro("quan_tri_chuoi")
@require_POST
def dat_dai_dien(request, loai, ma, id_anh):
    doi_tuong = get_object_or_404(CO_ANH[loai][0], pk=ma)
    try:
        dich_vu.dat_anh_dai_dien(request.user, loai, doi_tuong, id_anh)
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    else:
        messages.success(request, "Đã đổi ảnh đại diện.")
    return _ve_trang_sua(loai, ma)
