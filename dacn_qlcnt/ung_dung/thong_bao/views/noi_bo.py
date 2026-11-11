"""Khu quản lý: nhật ký email hệ thống, xem lại thư và gửi lại thư lỗi."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.chung.loc_danh_sach import BoLoc, OChon, o_khoang_thoi_gian
from ung_dung.chung.permissions import thay_toan_chuoi, yeu_cau_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from ..models import LOAI_EMAIL
from ..selectors import dem_theo_trang_thai, lay_nhat_ky_email
from ..services import dieu_kien_can_gui_lai, gui_lai, ly_do_khong_gui_lai

LOC_KET_QUA = [
    ("can_gui_lai", "Cần xử lý: lỗi hoặc kẹt"),
    ("loi", "Gửi lỗi"),
    ("cho_gui", "Chờ gửi"),
    ("da_gui", "Đã gửi"),
]


def _loc_ket_qua(tap_hop, gia_tri):
    if gia_tri == "can_gui_lai":
        return tap_hop.filter(dieu_kien_can_gui_lai())
    return tap_hop.filter(trang_thai=gia_tri)


def _bo_loc(request):
    cac_o = [
        OChon("trang_thai", "Kết quả", LOC_KET_QUA, ham_loc=_loc_ket_qua),
        OChon("loai_email", "Loại thư", LOAI_EMAIL, "loai_email"),
    ]
    if thay_toan_chuoi(request.user):
        cac_o.append(
            OChon(
                "chi_nhanh",
                "Chi nhánh của đơn",
                [(c.pk, c.ten_chi_nhanh) for c in lay_chi_nhanh(request.user)],
                "don_hang__chi_nhanh_id",
            )
        )
    cac_o.append(o_khoang_thoi_gian("thoi_diem_tao", "Tạo trong"))
    return BoLoc(
        request,
        cac_cot_tim=("email_nhan", "tieu_de", "don_hang__ma_don_hang"),
        nhan_tim="Email người nhận, tiêu đề, mã đơn",
        cac_o_chon=cac_o,
        mac_dinh_moi_trang=25,
    )


@yeu_cau_quyen("email.xem")
def nhat_ky_email(request):
    tap_hop = lay_nhat_ky_email(request.user)
    loc = _bo_loc(request)
    dem = dem_theo_trang_thai(tap_hop, dieu_kien_can_gui_lai())
    ngu_canh = loc.ngu_canh(tap_hop)
    for email in ngu_canh["trang"]:
        email.ly_do_khong_gui_lai_luc_nay = ly_do_khong_gui_lai(email)
    return render(
        request,
        "thong_bao/nhat_ky_email.html",
        {**ngu_canh, "dem": dem, "toan_chuoi": thay_toan_chuoi(request.user)},
    )


@yeu_cau_quyen("email.xem")
def chi_tiet(request, ma):
    email = get_object_or_404(lay_nhat_ky_email(request.user), pk=ma)
    return render(
        request,
        "thong_bao/nhat_ky_email_chi_tiet.html",
        {"email": email, "ly_do_khong_gui_lai": ly_do_khong_gui_lai(email)},
    )


@require_POST
@yeu_cau_quyen("email.xem")
def gui_lai_thu(request, ma):
    email = get_object_or_404(lay_nhat_ky_email(request.user), pk=ma)
    try:
        ket_qua = gui_lai(request.user, email)
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    else:
        if ket_qua.trang_thai == "da_gui":
            messages.success(request, f"Đã gửi lại thư tới {ket_qua.email_nhan}.")
        else:
            messages.error(request, f"Vẫn chưa gửi được: {ket_qua.chi_tiet_loi}")
    tiep = request.POST.get("tiep", "")
    if tiep == "chi_tiet":
        return redirect("thong_bao:nhat_ky_email_chi_tiet", ma=email.pk)
    return redirect("thong_bao:nhat_ky_email")
