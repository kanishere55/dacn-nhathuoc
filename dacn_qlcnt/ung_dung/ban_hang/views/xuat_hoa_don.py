"""Nhân sự chi nhánh xử lý yêu cầu hóa đơn công ty của khách."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.chung.permissions import NHAN_SU_CHI_NHANH, NHAN_SU_CHUOI, co_vai_tro, yeu_cau_vai_tro

from ..forms import XuLyXuatHoaDonForm
from ..models import TRANG_THAI_XUAT_HOA_DON
from ..selectors import lay_yeu_cau_xuat_hoa_don
from ..services.xuat_hoa_don import xu_ly_yeu_cau_xuat_hoa_don


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def danh_sach(request):
    trang_thai = request.GET.get("trang_thai", "")
    if trang_thai not in dict(TRANG_THAI_XUAT_HOA_DON):
        trang_thai = ""
    return render(
        request,
        "ban_hang/xuat_hoa_don_danh_sach.html",
        {
            "trang": Paginator(
                lay_yeu_cau_xuat_hoa_don(request.user, trang_thai=trang_thai), 30
            ).get_page(request.GET.get("page")),
            "trang_thai": trang_thai,
            "cac_trang_thai": TRANG_THAI_XUAT_HOA_DON,
            "duoc_xu_ly": co_vai_tro(request.user, *NHAN_SU_CHI_NHANH),
            # Mỗi dòng có một form; bỏ id tự sinh để không trùng id trên trang.
            "form_xu_ly": XuLyXuatHoaDonForm(auto_id=False),
        },
    )


@require_POST
@yeu_cau_vai_tro(*NHAN_SU_CHI_NHANH)
def xu_ly(request, ma):
    yeu_cau = get_object_or_404(lay_yeu_cau_xuat_hoa_don(request.user), pk=ma)
    form = XuLyXuatHoaDonForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Chọn kết quả và ghi số hóa đơn hoặc lý do từ chối.")
        return redirect("ban_hang:xuat_hoa_don_danh_sach")
    try:
        xu_ly_yeu_cau_xuat_hoa_don(
            request.user,
            yeu_cau,
            form.cleaned_data["trang_thai"],
            form.cleaned_data["ghi_chu_xu_ly"],
        )
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    else:
        messages.success(request, f"Đã cập nhật hóa đơn công ty của đơn {yeu_cau.don_hang}.")
    return redirect("ban_hang:xuat_hoa_don_danh_sach")
