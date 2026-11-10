"""Trò chuyện phía nhân sự: hộp thư chia theo loại, phòng chat kèm thông tin khách và đơn."""

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from ung_dung.ban_hang.selectors import lay_don
from ung_dung.chung.permissions import yeu_cau_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from ..selectors import LOC_HOP_THU, dem_hop_thu, lay_cac_phong, lay_hop_thu, lay_lich_su
from ..services import mo_phong_don_hang


@yeu_cau_quyen("tro_chuyen.dung")
@require_GET
def danh_sach(request):
    loc = request.GET.get("loc", "")
    loc = loc if loc in dict(LOC_HOP_THU) else ""
    return render(
        request,
        "tro_chuyen/danh_sach.html",
        {
            "cac_phong": lay_hop_thu(request.user, loc),
            "loc": loc,
            "cac_loc": LOC_HOP_THU,
            "dem": dem_hop_thu(request.user),
            "nhieu_chi_nhanh": lay_chi_nhanh(request.user).count() > 1,
        },
    )


@yeu_cau_quyen("tro_chuyen.dung")
@require_GET
def chi_tiet(request, ma):
    phong = get_object_or_404(lay_cac_phong(request.user), pk=ma)
    # Bảng bên cạnh: đơn đang trao đổi, hoặc các đơn gần đây của khách để tư vấn đúng ngữ cảnh.
    don_gan_day = (
        []
        if phong.la_don_hang
        else list(lay_don(request.user).filter(khach_hang=phong.khach_hang)[:5])
    )
    return render(
        request,
        "tro_chuyen/chi_tiet.html",
        {
            "phong": phong,
            "lich_su": lay_lich_su(request.user, phong),
            "don_gan_day": don_gan_day,
            "cac_phong_cung_khach": lay_cac_phong(request.user)
            .filter(khach_hang=phong.khach_hang)
            .exclude(pk=phong.pk)[:6],
        },
    )


@yeu_cau_quyen("tro_chuyen.dung")
@require_POST
def tu_don_hang(request, ma):
    """Nhân sự mở phòng về đơn để liên hệ khách (ví dụ báo hết hàng, hẹn giờ giao)."""
    don = get_object_or_404(lay_don(request.user), pk=ma)
    phong = mo_phong_don_hang(request.user, don)
    return redirect("tro_chuyen:chi_tiet", ma=phong.pk)
