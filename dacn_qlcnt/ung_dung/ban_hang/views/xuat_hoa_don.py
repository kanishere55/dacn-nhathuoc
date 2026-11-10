"""Nhân sự chi nhánh xử lý yêu cầu hóa đơn công ty của khách."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.chung.loc_danh_sach import BoLoc, OChon, o_khoang_thoi_gian
from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from ..forms import XuLyXuatHoaDonForm
from ..models import TRANG_THAI_XUAT_HOA_DON
from ..selectors import lay_yeu_cau_xuat_hoa_don
from ..services.xuat_hoa_don import xu_ly_yeu_cau_xuat_hoa_don


@yeu_cau_quyen("hoa_don_cong_ty.xem")
def danh_sach(request):
    loc = BoLoc(
        request,
        cac_cot_tim=(
            "ten_cong_ty",
            "ma_so_thue",
            "email_nhan_hoa_don",
            "don_hang__ma_don_hang",
        ),
        nhan_tim="Công ty, mã số thuế, email, mã đơn",
        cac_o_chon=[
            OChon("trang_thai", "Trạng thái", TRANG_THAI_XUAT_HOA_DON, "trang_thai"),
            OChon(
                "chi_nhanh",
                "Chi nhánh",
                [
                    (c.pk, c.ten_chi_nhanh)
                    for c in lay_chi_nhanh(request.user, ca_chi_nhanh_ngung=True)
                ],
                "don_hang__chi_nhanh_id",
            ),
            o_khoang_thoi_gian("thoi_diem_tao", "Gửi trong"),
        ],
        mac_dinh_moi_trang=25,
    )
    return render(
        request,
        "ban_hang/xuat_hoa_don_danh_sach.html",
        {
            **loc.ngu_canh(lay_yeu_cau_xuat_hoa_don(request.user)),
            "duoc_xu_ly": co_quyen(request.user, "hoa_don_cong_ty.xu_ly"),
            # Mỗi dòng có một form; bỏ id tự sinh để không trùng id trên trang.
            "form_xu_ly": XuLyXuatHoaDonForm(auto_id=False),
        },
    )


@require_POST
@yeu_cau_quyen("hoa_don_cong_ty.xu_ly")
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
