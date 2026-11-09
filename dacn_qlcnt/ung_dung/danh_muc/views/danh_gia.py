"""Quản trị chuỗi kiểm duyệt đánh giá: ẩn nhận xét vi phạm, không xóa dữ liệu."""

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.chung.permissions import yeu_cau_vai_tro

from ..models import DanhGiaThuoc


@yeu_cau_vai_tro("quan_tri_chuoi")
def danh_sach(request):
    cac_danh_gia = DanhGiaThuoc.objects.select_related("thuoc", "khach_hang")
    return render(
        request,
        "danh_muc/danh_gia_danh_sach.html",
        {"trang": Paginator(cac_danh_gia, 30).get_page(request.GET.get("page"))},
    )


@require_POST
@yeu_cau_vai_tro("quan_tri_chuoi")
def doi_hien_thi(request, ma):
    danh_gia = get_object_or_404(DanhGiaThuoc, pk=ma)
    danh_gia.dang_hien_thi = not danh_gia.dang_hien_thi
    danh_gia.save(update_fields=["dang_hien_thi"])
    return redirect(request.POST.get("next") or "danh_muc:danh_gia_danh_sach")
