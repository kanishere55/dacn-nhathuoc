"""Khu quản lý: quản trị chuỗi tạo nhóm quyền và chọn từng quyền cho nhóm."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.chung.permissions import yeu_cau_quyen

from ..forms import NhomQuyenForm
from ..models import NhomQuyen
from ..services.quyen import bao_dam_nhom_mac_dinh, luu_nhom_quyen, xoa_nhom_quyen


@yeu_cau_quyen("phan_quyen.quan_ly")
def danh_sach(request):
    bao_dam_nhom_mac_dinh()
    cac_nhom = NhomQuyen.objects.annotate(
        so_quyen=Count("cac_quyen", distinct=True),
        so_tai_khoan=Count("cac_tai_khoan", distinct=True),
    ).order_by("vai_tro_mac_dinh", "ten_nhom_quyen")
    return render(request, "tai_khoan/nhom_quyen_danh_sach.html", {"cac_nhom": cac_nhom})


@yeu_cau_quyen("phan_quyen.quan_ly")
def chinh_sua(request, ma=None):
    nhom = get_object_or_404(NhomQuyen, pk=ma) if ma else None
    form = NhomQuyenForm(request.POST or None, nhom=nhom)
    if request.method == "POST" and form.is_valid():
        try:
            luu_nhom_quyen(request.user, form.cleaned_data, form.cleaned_data["cac_quyen"], nhom)
        except ValidationError as loi:
            form.add_error(None, loi)
        except IntegrityError:
            form.add_error(None, "Mã nhóm trùng hoặc dữ liệu đã được thay đổi.")
        else:
            messages.success(request, "Đã lưu nhóm quyền.")
            return redirect("tai_khoan:nhom_quyen_danh_sach")
    return render(
        request,
        "tai_khoan/nhom_quyen_form.html",
        {"form": form, "nhom": nhom, "tieu_de": "Sửa nhóm quyền" if nhom else "Thêm nhóm quyền"},
    )


@require_POST
@yeu_cau_quyen("phan_quyen.quan_ly")
def xoa(request, ma):
    nhom = get_object_or_404(NhomQuyen, pk=ma)
    try:
        xoa_nhom_quyen(request.user, nhom)
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    else:
        messages.success(request, "Đã xóa nhóm quyền.")
    return redirect("tai_khoan:nhom_quyen_danh_sach")
