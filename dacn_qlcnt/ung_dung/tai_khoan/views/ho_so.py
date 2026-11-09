"""Trang tài khoản của người đã đăng nhập: hồ sơ, mật khẩu, email, sổ địa chỉ."""

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from ung_dung.ban_hang.thanh_vien import CAC_HANG, hang_cua
from ung_dung.chung.duong_dan import quay_lai
from ung_dung.chung.permissions import MOI_VAI_TRO, co_vai_tro, yeu_cau_vai_tro

from ..forms import DiaChiGiaoHangForm, DoiEmailForm, DoiMatKhauForm, HoSoForm, MaOTPForm
from ..selectors import cac_dia_chi_cua, lay_dia_chi_cua
from ..services import dia_chi_giao_hang, ho_so, xac_thuc
from .khach import ghi_phien, lay_phien_cua_trinh_duyet, ngu_canh_nhap_ma


def khung(request):
    """Khách dùng khung tài khoản của website; nhân sự dùng khung khu quản lý."""
    if co_vai_tro(request.user, "khach_hang"):
        return "tai_khoan/khach/_khung_tai_khoan.html"
    return "tai_khoan/_khung_tai_khoan_noi_bo.html"


def _trang(request, ten, ngu_canh):
    return render(request, f"tai_khoan/khach/{ten}.html", {"khung": khung(request), **ngu_canh})


@yeu_cau_vai_tro("khach_hang")
def cua_toi(request):
    return _trang(
        request,
        "cua_toi",
        {
            "dia_chi_mac_dinh": request.user.dia_chi_giao_hang_mac_dinh,
            "so_dia_chi": cac_dia_chi_cua(request.user).count(),
            "hang": hang_cua(request.user) if request.user.vai_tro == "khach_hang" else None,
            "cac_hang": CAC_HANG,
        },
    )


@yeu_cau_vai_tro(*MOI_VAI_TRO)
@require_http_methods(["GET", "POST"])
def thong_tin(request):
    form = HoSoForm(
        request.POST if request.method == "POST" else None,
        initial={"ho_ten": request.user.ho_ten, "so_dien_thoai": request.user.so_dien_thoai},
    )
    if form.is_bound and form.is_valid():
        ho_so.cap_nhat_ho_so(request.user, **form.cleaned_data)
        messages.success(request, "Đã lưu hồ sơ.")
        return redirect("tai_khoan:thong_tin")
    return _trang(request, "thong_tin", {"form": form})


@yeu_cau_vai_tro(*MOI_VAI_TRO)
@require_http_methods(["GET", "POST"])
def doi_mat_khau(request):
    form = DoiMatKhauForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        try:
            tai_khoan = ho_so.doi_mat_khau(
                request.user,
                form.cleaned_data["mat_khau_hien_tai"],
                form.cleaned_data["mat_khau_moi"],
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            update_session_auth_hash(request, tai_khoan)
            messages.success(request, "Đã đổi mật khẩu.")
            return redirect("tai_khoan:doi_mat_khau")
    return _trang(request, "doi_mat_khau", {"form": form})


@yeu_cau_vai_tro(*MOI_VAI_TRO)
@require_http_methods(["GET", "POST"])
def doi_email(request):
    form = DoiEmailForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        try:
            phien = xac_thuc.bat_dau_doi_email(
                request.user, form.cleaned_data["email_moi"], form.cleaned_data["mat_khau_hien_tai"]
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            ghi_phien(request, phien)
            return redirect("tai_khoan:xac_thuc_doi_email", ma=phien.ma_phien_xac_thuc)
    return _trang(request, "doi_email", {"form": form})


@yeu_cau_vai_tro(*MOI_VAI_TRO)
@require_http_methods(["GET", "POST"])
def xac_thuc_doi_email(request, ma):
    phien = lay_phien_cua_trinh_duyet(request, ma, "doi_email")
    if phien.tai_khoan_id != request.user.pk:
        return redirect("tai_khoan:doi_email")
    form = MaOTPForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        try:
            xac_thuc.xac_nhan_doi_email(
                request.user, phien.ma_phien_xac_thuc, form.cleaned_data["ma_otp"]
            )
        except ValidationError as loi:
            form.add_error("ma_otp", loi)
        else:
            messages.success(request, "Đã cập nhật email.")
            return redirect("tai_khoan:thong_tin")
    return render(
        request,
        "tai_khoan/khach/nhap_ma.html",
        ngu_canh_nhap_ma(phien, form, tieu_de="Xác nhận email mới", nut="Xác nhận"),
    )


@yeu_cau_vai_tro("khach_hang")
def so_dia_chi(request):
    return _trang(
        request,
        "so_dia_chi",
        {
            "cac_dia_chi": cac_dia_chi_cua(request.user),
            "id_mac_dinh": request.user.dia_chi_giao_hang_mac_dinh_id,
            "toi_da": dia_chi_giao_hang.SO_DIA_CHI_TOI_DA,
        },
    )


@yeu_cau_vai_tro("khach_hang")
@require_http_methods(["GET", "POST"])
def luu_dia_chi(request, ma=None):
    dia_chi = lay_dia_chi_cua(request.user, ma) if ma else None
    if request.method == "POST":
        form = DiaChiGiaoHangForm(request.POST)
    elif dia_chi:
        form = DiaChiGiaoHangForm.tu_dia_chi(
            dia_chi, dia_chi.pk == request.user.dia_chi_giao_hang_mac_dinh_id
        )
    else:
        form = DiaChiGiaoHangForm(
            initial={
                "ten_nguoi_nhan": request.user.ho_ten,
                "so_dien_thoai": request.user.so_dien_thoai,
            }
        )
    if form.is_bound and form.is_valid():
        try:
            dia_chi_giao_hang.luu_dia_chi(request.user, form.cleaned_data, dia_chi)
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            messages.success(request, "Đã lưu địa chỉ.")
            return quay_lai(request, "tai_khoan:so_dia_chi")
    return _trang(request, "dia_chi_form", {"form": form, "dia_chi": dia_chi})


@yeu_cau_vai_tro("khach_hang")
@require_POST
def xoa_dia_chi(request, ma):
    dia_chi_giao_hang.xoa_dia_chi(request.user, lay_dia_chi_cua(request.user, ma))
    messages.success(request, "Đã xóa địa chỉ.")
    return redirect("tai_khoan:so_dia_chi")


@yeu_cau_vai_tro("khach_hang")
@require_POST
def dat_dia_chi_mac_dinh(request, ma):
    dia_chi_giao_hang.dat_mac_dinh(request.user, lay_dia_chi_cua(request.user, ma))
    messages.success(request, "Đã đổi địa chỉ mặc định.")
    return redirect("tai_khoan:so_dia_chi")
