from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from ung_dung.chung.duong_dan import quay_lai
from ung_dung.chung.permissions import kiem_tra_vai_tro
from ung_dung.danh_muc.selectors import lay_thuoc_cong_khai

from ..forms import SuaSoLuongGioForm, ThemThuocVaoGioForm
from ..gio_hang import SO_LUONG_TOI_DA
from ..selectors import lay_dong_gio, lay_gio, tom_tat_gio
from ..services.gio_hang import sua_so_luong, them_thuoc


def _chi_khach(request):
    """Khách vãng lai và khách hàng dùng giỏ; nhân sự không mua trên website."""
    if request.user.is_authenticated:
        kiem_tra_vai_tro(request.user, "khach_hang")


@require_GET
def gio_hang(request):
    _chi_khach(request)
    cac_dong = lay_dong_gio(lay_gio(request.session))
    return render(
        request,
        "ban_hang/khach/gio_hang.html",
        {"cac_dong": cac_dong, "tom_tat": tom_tat_gio(cac_dong), "toi_da": SO_LUONG_TOI_DA},
    )


@require_POST
def them_vao_gio(request, ma):
    _chi_khach(request)
    thuoc = get_object_or_404(lay_thuoc_cong_khai(), ma_thuoc=ma)
    form = ThemThuocVaoGioForm(request.POST)
    if not form.is_valid():
        messages.error(request, f"Số lượng phải từ 1 đến {SO_LUONG_TOI_DA}.")
        return redirect("danh_muc:khach_thuoc_chi_tiet", ma=ma)
    try:
        them_thuoc(request.session, thuoc, form.cleaned_data["so_luong"])
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    else:
        messages.success(request, f"Đã thêm {thuoc.ten_thuoc} vào giỏ hàng.")
    return quay_lai(request, "ban_hang:gio_hang")


@require_POST
def sua_gio(request, ma):
    _chi_khach(request)
    form = SuaSoLuongGioForm(request.POST)
    if form.is_valid():
        try:
            sua_so_luong(request.session, ma, form.cleaned_data["so_luong"])
        except ValidationError as loi:
            messages.error(request, " ".join(loi.messages))
    else:
        messages.error(request, f"Số lượng phải từ 0 đến {SO_LUONG_TOI_DA}.")
    return redirect("ban_hang:gio_hang")
