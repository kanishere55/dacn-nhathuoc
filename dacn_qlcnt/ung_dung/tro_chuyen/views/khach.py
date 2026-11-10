"""Trò chuyện phía khách: hộp thư kiểu messenger, mở phòng tư vấn hoặc phòng theo đơn.

Thêm ?nhung=1 để hiện gọn trong khung chat nổi (iframe cùng nguồn) trên mọi trang khách.
"""

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from ung_dung.ban_hang.models import DonHang
from ung_dung.chung.permissions import yeu_cau_vai_tro
from ung_dung.danh_muc.selectors import lay_chi_nhanh_cong_khai

from ..forms import MoPhongForm
from ..selectors import chi_nhanh_goi_y, dem_chua_doc, lay_cac_phong, lay_hop_thu, lay_lich_su
from ..services import gui_tin_dau, mo_phong, mo_phong_don_hang

# Câu hỏi hay gặp, bấm để điền sẵn vào ô nhập của phòng tư vấn.
GOI_Y_TU_VAN = [
    "Nhà thuốc còn thuốc này không?",
    "Thuốc này dùng cho trẻ em được không?",
    "Uống thuốc trước hay sau ăn?",
    "Tôi đang mang thai, dùng được không?",
]


def _nhung(request):
    return request.GET.get("nhung") == "1" or request.POST.get("nhung") == "1"


def _toi_phong(request, phong):
    url = reverse("tro_chuyen:khach_chi_tiet", args=[phong.pk])
    return redirect(url + ("?nhung=1" if _nhung(request) else ""))


def _hien_thi(request, *, phong=None, form=None):
    if form is None:
        ma = request.GET.get("chi_nhanh", "")[:32]
        chi_nhanh = lay_chi_nhanh_cong_khai().filter(ma_chi_nhanh=ma).first() if ma else None
        form = MoPhongForm(
            initial={"chi_nhanh": chi_nhanh.pk if chi_nhanh else chi_nhanh_goi_y(request.user)}
        )
    return render(
        request,
        "tro_chuyen/khach/hop_thu.html",
        {
            "cac_phong": lay_hop_thu(request.user),
            "phong": phong,
            "lich_su": lay_lich_su(request.user, phong) if phong else None,
            "form": form,
            "nhung": _nhung(request),
            # Màn hẹp / khung nổi chỉ hiện một cột: ?moi=1 (hoặc form lỗi) mở khung hỏi mới.
            "hoi_moi": request.GET.get("moi") == "1" or form.is_bound,
            "goi_y_tu_van": GOI_Y_TU_VAN,
        },
    )


@xframe_options_sameorigin
@yeu_cau_vai_tro("khach_hang")
@require_http_methods(["GET", "POST"])
def danh_sach(request):
    """Hộp thư; POST mở phòng tư vấn với nhà thuốc đã chọn và gửi câu hỏi đầu tiên nếu có."""
    if request.method == "POST":
        form = MoPhongForm(request.POST)
        if form.is_valid():
            try:
                phong = mo_phong(request.user, form.cleaned_data["chi_nhanh"])
                if form.cleaned_data["noi_dung"].strip():
                    gui_tin_dau(request.user, phong, form.cleaned_data["noi_dung"])
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


@yeu_cau_vai_tro("khach_hang")
@require_POST
def tu_don_hang(request, ma):
    """Nút "Nhắn nhà thuốc" ở trang đơn: vào thẳng phòng của đơn, không phải chọn chi nhánh."""
    don = get_object_or_404(DonHang, pk=ma, khach_hang=request.user)
    return _toi_phong(request, mo_phong_don_hang(request.user, don))


@require_GET
def so_chua_doc(request):
    """Số tin chưa đọc của người đang đăng nhập; dùng khi kênh thời gian thực bị gián đoạn."""
    if not request.user.is_authenticated:
        return JsonResponse({"tong": 0})
    return JsonResponse({"tong": dem_chua_doc(request.user)})
