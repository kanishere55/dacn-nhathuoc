from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.chung.permissions import yeu_cau_vai_tro

from .forms import DangKyForm, DangNhapForm, TaiKhoanForm
from .selectors import lay_tai_khoan
from .services import dang_ky_khach, luu_tai_khoan


def dang_nhap(request):
    form = DangNhapForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("chung:trang_chu")
    return render(request, "tai_khoan/dang_nhap.html", {"form": form, "tieu_de": "Đăng nhập"})


@require_POST
def dang_xuat(request):
    logout(request)
    return redirect("tai_khoan:dang_nhap")


def dang_ky(request):
    form = DangKyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
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
            return redirect("chung:trang_chu")
    return render(
        request, "tai_khoan/dang_nhap.html", {"form": form, "tieu_de": "Đăng ký khách hàng"}
    )


@yeu_cau_vai_tro("quan_tri_chuoi")
def danh_sach(request):
    return render(
        request, "tai_khoan/danh_sach.html", {"cac_tai_khoan": lay_tai_khoan(request.user)}
    )


@yeu_cau_vai_tro("quan_tri_chuoi")
def chinh_sua(request, ma=None):
    doi_tuong = get_object_or_404(lay_tai_khoan(request.user), pk=ma) if ma else None
    form = TaiKhoanForm(request.POST or None, instance=doi_tuong)
    if request.method == "POST" and form.is_valid():
        try:
            luu_tai_khoan(request.user, form.cleaned_data, doi_tuong)
        except ValidationError as loi:
            form.add_error(None, loi)
        except IntegrityError:
            form.add_error(None, "Tài khoản trùng hoặc dữ liệu đã thay đổi.")
        else:
            return redirect("tai_khoan:danh_sach")
    return render(request, "tai_khoan/form.html", {"form": form, "tieu_de": "Tài khoản"})
