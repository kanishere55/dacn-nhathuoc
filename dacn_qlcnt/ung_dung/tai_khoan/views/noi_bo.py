from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import yeu_cau_vai_tro

from ..forms import TaiKhoanForm
from ..selectors import lay_tai_khoan
from ..services import luu_tai_khoan


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
