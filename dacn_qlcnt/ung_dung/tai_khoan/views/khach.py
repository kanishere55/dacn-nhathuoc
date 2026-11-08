from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from ung_dung.chung.permissions import NHAN_SU_CHUOI, co_vai_tro, yeu_cau_vai_tro

from ..forms import DangKyForm, DangNhapForm
from ..services import dang_ky_khach


@require_http_methods(["GET", "POST"])
def dang_nhap(request):
    form = DangNhapForm(request, data=request.POST if request.method == "POST" else None)
    quay_lai = request.POST.get("next", request.GET.get("next", ""))
    if form.is_bound and form.is_valid():
        nguoi = form.get_user()
        login(request, nguoi)
        if co_vai_tro(nguoi, *NHAN_SU_CHUOI):
            return redirect("chung:bang_dieu_khien")
        if url_has_allowed_host_and_scheme(
            quay_lai, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(quay_lai)
        return redirect("chung:trang_chu")
    return render(
        request,
        "tai_khoan/khach/dang_nhap.html",
        {"form": form, "tieu_de": "Đăng nhập", "quay_lai": quay_lai},
    )


@require_POST
def dang_xuat(request):
    logout(request)
    return redirect("tai_khoan:dang_nhap")


@require_http_methods(["GET", "POST"])
def dang_ky(request):
    form = DangKyForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        try:
            tai_khoan = dang_ky_khach(
                form.cleaned_data["ten_dang_nhap"], form.cleaned_data["mat_khau"]
            )
        except (ValidationError, ValueError) as loi:
            form.add_error(None, str(loi))
        except IntegrityError:
            form.add_error(None, "Tên đăng nhập không hợp lệ hoặc đã được sử dụng.")
        else:
            login(request, tai_khoan)
            return redirect("tai_khoan:cua_toi")
    return render(
        request,
        "tai_khoan/khach/dang_nhap.html",
        {"form": form, "tieu_de": "Đăng ký khách hàng", "dang_ky": True},
    )


@yeu_cau_vai_tro("khach_hang")
@require_GET
def cua_toi(request):
    return render(request, "tai_khoan/khach/cua_toi.html")
