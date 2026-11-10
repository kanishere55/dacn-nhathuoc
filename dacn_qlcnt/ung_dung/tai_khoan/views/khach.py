"""Đăng nhập, đăng ký có xác thực email và khôi phục tài khoản cho website khách."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from ung_dung.chung.duong_dan import la_duong_dan_noi_bo
from ung_dung.chung.permissions import NHAN_SU_CHUOI, co_vai_tro

from ..forms import DangKyForm, DangNhapForm, DatLaiMatKhauForm, EmailForm, MaOTPForm
from ..services import xac_thuc
from ..services.xac_thuc import GIAY_CHO_GUI_LAI, che_email

KHOA_PHIEN = "cac_phien_xac_thuc"
TRANG_NHAP_MA = {
    "dang_ky": "tai_khoan:xac_thuc_dang_ky",
    "quen_mat_khau": "tai_khoan:dat_lai_mat_khau",
    "doi_email": "tai_khoan:xac_thuc_doi_email",
}


def ghi_phien(request, phien):
    """Chỉ trình duyệt đã yêu cầu mã mới mở được trang nhập mã."""
    cac_phien = request.session.get(KHOA_PHIEN, [])[-4:]
    cac_phien.append(phien.ma_phien_xac_thuc)
    request.session[KHOA_PHIEN] = cac_phien


def lay_phien_cua_trinh_duyet(request, ma, loai):
    if str(ma) not in request.session.get(KHOA_PHIEN, []):
        raise Http404("Phiên xác thực không tồn tại.")
    phien = xac_thuc.lay_phien(str(ma), loai)
    if phien is None:
        raise Http404("Phiên xác thực không tồn tại.")
    return phien


def ngu_canh_nhap_ma(phien, form, **them):
    da_qua = (timezone.now() - phien.thoi_diem_gui_cuoi).total_seconds()
    return {
        "form": form,
        "phien": phien,
        "email_che": che_email(phien.email),
        "giay_cho": max(0, GIAY_CHO_GUI_LAI - int(da_qua)),
        "duong_dan_gui_lai": reverse("tai_khoan:gui_lai_ma", args=[phien.ma_phien_xac_thuc]),
        **them,
    }


def _trang_sau_dang_nhap(request, nguoi, quay_lai):
    hop_le = la_duong_dan_noi_bo(request, quay_lai)
    if co_vai_tro(nguoi, *NHAN_SU_CHUOI):
        # Nhân sự quay lại đúng trang quản lý đang mở dở (ví dụ khi hết phiên), còn lại về bảng điều khiển.
        quan_ly = reverse("chung:bang_dieu_khien")
        if hop_le and quay_lai.startswith(quan_ly):
            return redirect(quay_lai)
        return redirect("chung:bang_dieu_khien")
    if hop_le:
        return redirect(quay_lai)
    return redirect("chung:trang_chu")


@require_http_methods(["GET", "POST"])
def dang_nhap(request):
    quay_lai = request.POST.get("next", request.GET.get("next", ""))
    if request.user.is_authenticated and request.method == "GET":
        return _trang_sau_dang_nhap(request, request.user, quay_lai)
    form = DangNhapForm(request, data=request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        login(request, form.get_user())
        return _trang_sau_dang_nhap(request, form.get_user(), quay_lai)
    return render(request, "tai_khoan/khach/dang_nhap.html", {"form": form, "quay_lai": quay_lai})


@require_POST
def dang_xuat(request):
    logout(request)
    messages.success(request, "Bạn đã đăng xuất.")
    return redirect("chung:trang_chu")


@require_http_methods(["GET", "POST"])
def dang_ky(request):
    if request.user.is_authenticated:
        return redirect("chung:trang_chu")
    form = DangKyForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        du_lieu = {
            ten: gia_tri for ten, gia_tri in form.cleaned_data.items() if ten != "nhap_lai_mat_khau"
        }
        try:
            phien = xac_thuc.bat_dau_dang_ky(**du_lieu)
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            ghi_phien(request, phien)
            return redirect("tai_khoan:xac_thuc_dang_ky", ma=phien.ma_phien_xac_thuc)
    return render(request, "tai_khoan/khach/dang_ky.html", {"form": form})


@require_http_methods(["GET", "POST"])
def xac_thuc_dang_ky(request, ma):
    phien = lay_phien_cua_trinh_duyet(request, ma, "dang_ky")
    form = MaOTPForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        try:
            tai_khoan = xac_thuc.hoan_tat_dang_ky(
                phien.ma_phien_xac_thuc, form.cleaned_data["ma_otp"]
            )
        except ValidationError as loi:
            form.add_error("ma_otp", loi)
        else:
            login(request, tai_khoan)
            messages.success(request, "Đăng ký thành công. Chào mừng bạn!")
            return redirect("tai_khoan:cua_toi")
    return render(
        request,
        "tai_khoan/khach/nhap_ma.html",
        ngu_canh_nhap_ma(phien, form, tieu_de="Xác thực email", nut="Hoàn tất đăng ký"),
    )


@require_POST
def gui_lai_ma(request, ma):
    if str(ma) not in request.session.get(KHOA_PHIEN, []):
        raise Http404("Phiên xác thực không tồn tại.")
    phien = next((p for loai in TRANG_NHAP_MA if (p := xac_thuc.lay_phien(str(ma), loai))), None)
    if phien is None or (
        phien.loai_xac_thuc == "doi_email" and phien.tai_khoan_id != request.user.pk
    ):
        raise Http404("Phiên xác thực không tồn tại.")
    try:
        xac_thuc.gui_lai_ma(phien.ma_phien_xac_thuc, phien.loai_xac_thuc)
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    else:
        messages.success(request, f"Đã gửi mã mới tới {che_email(phien.email)}.")
    return redirect(TRANG_NHAP_MA[phien.loai_xac_thuc], ma=phien.ma_phien_xac_thuc)


@require_http_methods(["GET", "POST"])
def quen_mat_khau(request):
    form = EmailForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        try:
            phien = xac_thuc.bat_dau_quen_mat_khau(form.cleaned_data["email"])
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            ghi_phien(request, phien)
            return redirect("tai_khoan:dat_lai_mat_khau", ma=phien.ma_phien_xac_thuc)
    return render(
        request,
        "tai_khoan/khach/quen.html",
        {
            "form": form,
            "tieu_de": "Quên mật khẩu",
            "mo_ta": "Nhập email đã đăng ký. Nếu email thuộc một tài khoản, chúng tôi sẽ gửi mã để đặt lại mật khẩu.",
            "nut": "Gửi mã xác thực",
        },
    )


@require_http_methods(["GET", "POST"])
def dat_lai_mat_khau(request, ma):
    phien = lay_phien_cua_trinh_duyet(request, ma, "quen_mat_khau")
    form = DatLaiMatKhauForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        try:
            xac_thuc.dat_lai_mat_khau(
                phien.ma_phien_xac_thuc,
                form.cleaned_data["ma_otp"],
                form.cleaned_data["mat_khau_moi"],
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            messages.success(request, "Đã đặt lại mật khẩu. Hãy đăng nhập bằng mật khẩu mới.")
            return redirect("tai_khoan:dang_nhap")
    return render(
        request,
        "tai_khoan/khach/nhap_ma.html",
        ngu_canh_nhap_ma(
            phien,
            form,
            tieu_de="Đặt lại mật khẩu",
            nut="Đặt lại mật khẩu",
            ghi_chu="Nếu email này có tài khoản, mã đã được gửi tới hộp thư.",
        ),
    )


@require_http_methods(["GET", "POST"])
def quen_ten_dang_nhap(request):
    form = EmailForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        xac_thuc.nhac_ten_dang_nhap(form.cleaned_data["email"])
        messages.success(
            request,
            "Nếu email thuộc một tài khoản, tên đăng nhập đã được gửi tới hộp thư của bạn.",
        )
        return redirect("tai_khoan:dang_nhap")
    return render(
        request,
        "tai_khoan/khach/quen.html",
        {
            "form": form,
            "tieu_de": "Quên tên đăng nhập",
            "mo_ta": "Nhập email đã đăng ký, chúng tôi sẽ gửi tên đăng nhập tới hộp thư đó.",
            "nut": "Gửi tên đăng nhập",
        },
    )
