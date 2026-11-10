"""Trò chuyện phía khách: hộp thư kiểu messenger, hỏi dược sĩ hoặc nhắn về một đơn.

Thêm ?nhung=1 để hiện gọn trong khung chat nổi (iframe cùng nguồn) trên mọi trang khách.
Mở trang soạn tin không tạo gì cả; cuộc trò chuyện chỉ xuất hiện khi tin đầu tiên được gửi.
"""

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_http_methods

from ung_dung.ban_hang.models import DonHang
from ung_dung.chung.permissions import yeu_cau_vai_tro
from ung_dung.danh_muc.selectors import lay_chi_nhanh_cong_khai

from ..forms import MoPhongForm, TinDauVeDonForm
from ..selectors import (
    chi_nhanh_goi_y,
    dem_chua_doc,
    lay_cac_phong,
    lay_hop_thu,
    lay_lich_su,
    lay_tin_cu,
)
from ..services import bat_dau_tu_van, bat_dau_ve_don
from ._chung import so_truoc

# Câu hỏi hay gặp, bấm để điền sẵn vào ô nhập của phòng tư vấn.
GOI_Y_TU_VAN = [
    "Nhà thuốc còn thuốc này không?",
    "Thuốc này dùng cho trẻ em được không?",
    "Uống thuốc trước hay sau ăn?",
    "Tôi đang mang thai, dùng được không?",
]
GOI_Y_VE_DON = [
    "Khi nào tôi nhận được hàng?",
    "Tôi muốn đổi giờ nhận hàng.",
    "Tôi muốn thêm hoặc bớt thuốc trong đơn.",
]
SO_PHONG_MOI_TRANG = 30


def _nhung(request):
    return request.GET.get("nhung") == "1" or request.POST.get("nhung") == "1"


def _toi_phong(request, phong):
    url = reverse("tro_chuyen:khach_chi_tiet", args=[phong.pk])
    return redirect(url + ("?nhung=1" if _nhung(request) else ""))


def _hien_thi(request, *, phong=None, form=None, don_nhap=None, form_don=None):
    if form is None:
        ma = request.GET.get("chi_nhanh", "")[:32]
        chi_nhanh = lay_chi_nhanh_cong_khai().filter(ma_chi_nhanh=ma).first() if ma else None
        form = MoPhongForm(
            initial={"chi_nhanh": chi_nhanh.pk if chi_nhanh else chi_nhanh_goi_y(request.user)}
        )
    # Khách lâu năm có thể có hàng trăm cuộc trò chuyện về đơn: chia trang, mới nhất trước.
    trang = Paginator(lay_hop_thu(request.user), SO_PHONG_MOI_TRANG).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "tro_chuyen/khach/hop_thu.html",
        {
            "cac_phong": trang,
            "trang": trang,
            "phong": phong,
            "lich_su": lay_lich_su(request.user, phong) if phong else None,
            "form": form,
            "don_nhap": don_nhap,
            "form_don": form_don or TinDauVeDonForm(),
            "nhung": _nhung(request),
            # Màn hẹp / khung nổi chỉ hiện một cột: ?moi=1 (hoặc form lỗi) mở khung hỏi mới.
            "hoi_moi": request.GET.get("moi") == "1" or form.is_bound or don_nhap is not None,
            "goi_y_tu_van": GOI_Y_TU_VAN,
            "goi_y_ve_don": GOI_Y_VE_DON,
        },
    )


@xframe_options_sameorigin
@yeu_cau_vai_tro("khach_hang")
@require_http_methods(["GET", "POST"])
def danh_sach(request):
    """Hộp thư; POST gửi câu hỏi tới nhà thuốc đã chọn (tạo cuộc trò chuyện nếu chưa có)."""
    if request.method == "POST":
        form = MoPhongForm(request.POST)
        if form.is_valid():
            try:
                phong = bat_dau_tu_van(
                    request.user, form.cleaned_data["chi_nhanh"], form.cleaned_data["noi_dung"]
                )
            except ValidationError as loi:
                form.add_error(None, loi)
            else:
                return _toi_phong(request, phong)
        return _hien_thi(request, form=form)
    return _hien_thi(request)


@xframe_options_sameorigin
@yeu_cau_vai_tro("khach_hang")
@require_GET
def chi_tiet(request, ma):
    phong = get_object_or_404(lay_cac_phong(request.user), pk=ma)
    return _hien_thi(request, phong=phong)


@xframe_options_sameorigin
@yeu_cau_vai_tro("khach_hang")
@require_http_methods(["GET", "POST"])
def tu_don_hang(request, ma):
    """Nút "Nhắn nhà thuốc" ở trang đơn: đã có cuộc trò chuyện thì vào thẳng, chưa có thì soạn
    tin đầu (không phải chọn chi nhánh). Chỉ khi bấm Gửi cuộc trò chuyện mới được tạo."""
    don = get_object_or_404(
        DonHang.objects.select_related("chi_nhanh"), pk=ma, khach_hang=request.user
    )
    phong = lay_cac_phong(request.user).filter(don_hang=don).first()
    if phong is not None:
        return _toi_phong(request, phong)
    form_don = TinDauVeDonForm(request.POST or None)
    if request.method == "POST" and form_don.is_valid():
        try:
            phong = bat_dau_ve_don(request.user, don, form_don.cleaned_data["noi_dung"])
        except ValidationError as loi:
            form_don.add_error(None, loi)
        else:
            return _toi_phong(request, phong)
    return _hien_thi(request, don_nhap=don, form_don=form_don)


@yeu_cau_vai_tro("khach_hang")
@require_GET
def tin_cu(request, ma):
    """Tải thêm tin cũ hơn khi khách kéo lên đầu cuộc trò chuyện dài."""
    phong = get_object_or_404(lay_cac_phong(request.user), pk=ma)
    return JsonResponse(lay_tin_cu(request.user, phong, so_truoc(request)))


@require_GET
def so_chua_doc(request):
    """Số tin chưa đọc của người đang đăng nhập; dùng khi kênh thời gian thực bị gián đoạn."""
    if not request.user.is_authenticated:
        return JsonResponse({"tong": 0})
    return JsonResponse({"tong": dem_chua_doc(request.user)})
