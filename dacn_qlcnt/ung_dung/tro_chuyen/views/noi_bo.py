"""Trò chuyện phía nhân sự: hộp thư dạng hàng chờ (tìm, lọc, phân trang), phòng chat kèm thông
tin khách và đơn, đánh dấu đã xong / mở lại, soạn tin đầu về một đơn."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from ung_dung.ban_hang.selectors import lay_don
from ung_dung.chung.loc_danh_sach import BoLoc, OChon
from ung_dung.chung.permissions import yeu_cau_quyen
from ung_dung.kho.loc import o_chi_nhanh

from ..forms import TinDauVeDonForm
from ..selectors import (
    HANG_CHO,
    LOAI_HOP_THU,
    dem_hang_cho,
    kem_tom_tat,
    lay_cac_phong,
    lay_lich_su,
    lay_tin_cu,
    loc_hang_cho,
    tim_phong,
)
from ..services import bat_dau_ve_don, danh_dau_xong, kiem_tra_nhan_ve_don, mo_lai
from ._chung import so_truoc


def _bo_loc(request):
    return BoLoc(
        request,
        ham_tim=tim_phong,  # tìm cả trong nội dung tin, không chỉ cột của phòng
        nhan_tim="Tên, SĐT khách, mã đơn hoặc nội dung tin",
        mac_dinh_moi_trang=25,
        cac_o_chon=[
            OChon("loai", "Loại", LOAI_HOP_THU, "loai_cuoc_tro_chuyen"),
            *o_chi_nhanh(request.user, "chi_nhanh_id"),
        ],
    )


@yeu_cau_quyen("tro_chuyen.dung")
@require_GET
def danh_sach(request):
    hang_cho = request.GET.get("trang_thai", "")
    hang_cho = hang_cho if hang_cho in dict(HANG_CHO) else "cho_tra_loi"
    loc = _bo_loc(request)
    cac_phong = loc.ap_dung(lay_cac_phong(request.user))
    dem = dem_hang_cho(cac_phong)
    trang = loc.trang(loc_hang_cho(kem_tom_tat(cac_phong, request.user), hang_cho))
    return render(
        request,
        "tro_chuyen/danh_sach.html",
        {
            "loc": loc,
            "trang": trang,
            "hang_cho": hang_cho,
            "cac_the": [(ma, nhan, dem[ma]) for ma, nhan in HANG_CHO],
            "nhieu_chi_nhanh": bool(o_chi_nhanh(request.user, "chi_nhanh_id")),
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
            .exclude(pk=phong.pk)
            .order_by("-tin_cuoi_id")[:6],
            "quay_lai": _hop_le(request.GET.get("quay_lai", "")),
        },
    )


def _hop_le(quay_lai):
    """Chỉ nhận đường dẫn của hộp thư (giữ thẻ, bộ lọc, trang đang xem); khác thì về hộp thư."""
    goc = reverse("tro_chuyen:danh_sach")
    return quay_lai if quay_lai == goc or quay_lai.startswith(goc + "?") else goc


def _ve_hop_thu(request):
    return redirect(_hop_le(request.POST.get("quay_lai", "")))


@yeu_cau_quyen("tro_chuyen.dung")
@require_POST
def xong(request, ma):
    phong = get_object_or_404(lay_cac_phong(request.user), pk=ma)
    danh_dau_xong(request.user, phong)
    messages.success(
        request,
        f"Đã chuyển cuộc trò chuyện với {phong.khach_hang.ho_ten or phong.khach_hang.ten_dang_nhap} "
        "sang Đã xong. Khách nhắn tiếp thì cuộc trò chuyện tự mở lại.",
    )
    return _ve_hop_thu(request)


@yeu_cau_quyen("tro_chuyen.dung")
@require_POST
def mo_lai_phong(request, ma):
    phong = get_object_or_404(lay_cac_phong(request.user), pk=ma)
    mo_lai(request.user, phong)
    messages.success(request, "Đã mở lại cuộc trò chuyện.")
    return redirect("tro_chuyen:chi_tiet", ma=phong.pk)


@yeu_cau_quyen("tro_chuyen.dung")
@require_http_methods(["GET", "POST"])
def tu_don_hang(request, ma):
    """Nhân sự liên hệ khách về đơn (báo hết hàng, hẹn giờ giao…). Đã có cuộc trò chuyện thì
    mở nó; chưa có thì soạn tin đầu, khách chỉ thấy cuộc trò chuyện khi tin được gửi."""
    don = get_object_or_404(lay_don(request.user), pk=ma)
    kiem_tra_nhan_ve_don(request.user, don)
    phong = lay_cac_phong(request.user).filter(don_hang=don).first()
    if phong is not None:
        return redirect("tro_chuyen:chi_tiet", ma=phong.pk)
    form = TinDauVeDonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            phong = bat_dau_ve_don(request.user, don, form.cleaned_data["noi_dung"])
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("tro_chuyen:chi_tiet", ma=phong.pk)
    return render(request, "tro_chuyen/soan_ve_don.html", {"don": don, "form": form})


@yeu_cau_quyen("tro_chuyen.dung")
@require_GET
def tin_cu(request, ma):
    phong = get_object_or_404(lay_cac_phong(request.user), pk=ma)
    return JsonResponse(lay_tin_cu(request.user, phong, so_truoc(request)))
