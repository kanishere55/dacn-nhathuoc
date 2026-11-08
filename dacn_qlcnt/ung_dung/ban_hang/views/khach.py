from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from ung_dung.chung.permissions import kiem_tra_vai_tro, yeu_cau_vai_tro
from ung_dung.danh_muc.selectors import lay_chi_nhanh_cong_khai, lay_thuoc_cong_khai
from ung_dung.kho.selectors import loc_chi_nhanh_du_thuoc

from ..forms import ChonChiNhanhGiuForm, SuaSoLuongGioForm, ThemThuocVaoGioForm
from ..gio_dat_giu import SO_LUONG_TOI_DA
from ..selectors import gio_duoc_giu, lay_chi_tiet_don, lay_don, lay_dong_gio, lay_gio
from ..services.dat_giu import huy_giu
from ..services.gio_dat_giu import sua_so_luong, them_thuoc, xac_nhan_gio


def _kiem_tra_quyen_gio(request):
    if request.user.is_authenticated:
        kiem_tra_vai_tro(request.user, "khach_hang")


@require_GET
def gio_dat_giu(request):
    _kiem_tra_quyen_gio(request)
    cac_dong = lay_dong_gio(lay_gio(request.session))
    hop_le = gio_duoc_giu(cac_dong)
    cac_chi_nhanh = lay_chi_nhanh_cong_khai()
    du_hang = loc_chi_nhanh_du_thuoc(cac_chi_nhanh, cac_dong) if hop_le else []
    ma_chi_nhanh = request.GET.get("chi_nhanh")
    duoc_chon = next((cn.pk for cn in du_hang if cn.ma_chi_nhanh == ma_chi_nhanh), None)
    url_gio = reverse("ban_hang:gio_dat_giu")
    return render(
        request,
        "ban_hang/khach/gio_dat_giu.html",
        {
            "cac_dong": cac_dong,
            "hop_le": hop_le,
            "co_chi_nhanh_du_hang": bool(du_hang),
            "gioi_han_so_luong": SO_LUONG_TOI_DA,
            "form": ChonChiNhanhGiuForm(
                cac_chi_nhanh=cac_chi_nhanh.filter(pk__in=[cn.pk for cn in du_hang]),
                initial={"chi_nhanh": duoc_chon},
            ),
            "url_dang_nhap": redirect_to_login(url_gio).url,
        },
    )


@require_POST
def them_vao_gio(request, ma):
    _kiem_tra_quyen_gio(request)
    thuoc = get_object_or_404(lay_thuoc_cong_khai(), ma_thuoc=ma)
    form = ThemThuocVaoGioForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Vui lòng nhập số lượng nguyên dương hợp lệ.")
        return redirect("danh_muc:khach_thuoc_chi_tiet", ma=ma)
    try:
        them_thuoc(request.session, thuoc, form.cleaned_data["so_luong"])
    except ValidationError as loi:
        messages.error(request, ". ".join(loi.messages))
    else:
        messages.success(request, f"Đã thêm {thuoc.ten_thuoc} vào giỏ.")
    return redirect("ban_hang:gio_dat_giu")


@require_POST
def sua_gio(request, ma):
    _kiem_tra_quyen_gio(request)
    form = SuaSoLuongGioForm(request.POST)
    if form.is_valid():
        try:
            sua_so_luong(request.session, ma, form.cleaned_data["so_luong"])
        except ValidationError as loi:
            messages.error(request, ". ".join(loi.messages))
    else:
        messages.error(request, "Vui lòng nhập số lượng hợp lệ.")
    return redirect("ban_hang:gio_dat_giu")


@require_POST
def xac_nhan_dat_giu(request):
    if not request.user.is_authenticated:
        return redirect_to_login(reverse("ban_hang:gio_dat_giu"))
    kiem_tra_vai_tro(request.user, "khach_hang")
    form = ChonChiNhanhGiuForm(request.POST, cac_chi_nhanh=lay_chi_nhanh_cong_khai())
    if not form.is_valid():
        messages.error(request, "Vui lòng chọn chi nhánh đang hoạt động.")
        return redirect("ban_hang:gio_dat_giu")
    try:
        don = xac_nhan_gio(request.session, request.user, form.cleaned_data["chi_nhanh"])
    except ValidationError as loi:
        messages.error(request, ". ".join(loi.messages))
        return redirect("ban_hang:gio_dat_giu")
    messages.success(request, "Đã đặt giữ thuốc. Vui lòng nhận và thanh toán tại quầy.")
    return redirect("ban_hang:khach_don_dat_giu_chi_tiet", ma=don.pk)


@yeu_cau_vai_tro("khach_hang")
@require_GET
def danh_sach_don(request):
    return render(request, "ban_hang/khach/don_dat_giu.html", {"cac_don": lay_don(request.user)})


@yeu_cau_vai_tro("khach_hang")
@require_GET
def chi_tiet_don(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    return render(
        request,
        "ban_hang/khach/chi_tiet_dat_giu.html",
        {"don": don, "cac_dong": lay_chi_tiet_don(don)},
    )


@require_POST
@yeu_cau_vai_tro("khach_hang")
def huy_don(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    try:
        huy_giu(request.user, don)
    except ValidationError as loi:
        messages.error(request, ". ".join(loi.messages))
    return redirect("ban_hang:khach_don_dat_giu_chi_tiet", ma=don.pk)
