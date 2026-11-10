"""Trò chuyện phía khách: hộp thư kiểu Shopee, mỗi nhà thuốc một cuộc trò chuyện duy nhất.

Hỏi tư vấn, hỏi về một sản phẩm hay một đơn hàng đều vào chung cuộc trò chuyện với nhà thuốc đó.
Đi từ trang thuốc (?thuoc=) hoặc trang đơn thì khung soạn tin hiện thẻ "Bạn đang hỏi về…" và
tin gửi kèm thẻ; nhắn thẳng thì không có thẻ.

Thêm ?nhung=1 để hiện gọn trong khung chat nổi (iframe cùng nguồn) trên mọi trang khách.
Mở trang soạn tin không tạo gì cả; cuộc trò chuyện chỉ xuất hiện khi tin đầu tiên được gửi.
"""

from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from ung_dung.ban_hang.models import DonHang
from ung_dung.chung.permissions import yeu_cau_vai_tro
from ung_dung.danh_muc.selectors import lay_chi_nhanh_cong_khai, lay_thuoc_cong_khai

from ..forms import MoPhongForm, TinDauVeDonForm
from ..selectors import (
    chi_nhanh_goi_y,
    dem_chua_doc,
    lay_cac_phong,
    lay_hop_thu,
    lay_lich_su,
    lay_tin_cu,
    phong_cua_don,
    the_don,
    the_thuoc,
)
from ..services import bat_dau_tro_chuyen, bat_dau_ve_don
from ._chung import gui_tin_kem_anh, so_truoc, the_don_cho_gui, xem_anh

# Câu hỏi hay gặp, bấm để điền sẵn vào ô nhập.
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


def _toi_phong(request, phong, **tham_so):
    if _nhung(request):
        tham_so["nhung"] = "1"
    url = reverse("tro_chuyen:khach_chi_tiet", args=[phong.pk])
    return redirect(url + (f"?{urlencode(tham_so)}" if tham_so else ""))


def _thuoc_dang_hoi(request):
    """Thuốc khách bấm "Hỏi dược sĩ" ở trang sản phẩm (?thuoc=<mã thuốc>), nếu còn bán."""
    ma = (request.GET.get("thuoc") or request.POST.get("thuoc") or "")[:64]
    return lay_thuoc_cong_khai().filter(ma_thuoc=ma).first() if ma else None


def _hien_thi(request, *, phong=None, form=None, don_nhap=None, form_don=None, thuoc=None):
    if form is None:
        ma = request.GET.get("chi_nhanh", "")[:32]
        chi_nhanh = lay_chi_nhanh_cong_khai().filter(ma_chi_nhanh=ma).first() if ma else None
        form = MoPhongForm(
            initial={"chi_nhanh": chi_nhanh.pk if chi_nhanh else chi_nhanh_goi_y(request.user)}
        )
    # Khách mua ở nhiều chi nhánh có nhiều cuộc trò chuyện: chia trang, mới nhất trước.
    trang = Paginator(lay_hop_thu(request.user), SO_PHONG_MOI_TRANG).get_page(
        request.GET.get("page")
    )
    the_cho = None
    if phong is not None:
        if thuoc is not None:
            the_cho = {"id": thuoc.pk, **the_thuoc(thuoc)}
        else:
            the_cho = the_don_cho_gui(request, phong)
    elif thuoc is not None:
        the_cho = {"id": thuoc.pk, **the_thuoc(thuoc)}
    elif don_nhap is not None:
        the_cho = {"id": don_nhap.pk, **the_don(don_nhap)}
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
            "thuoc_dang_hoi": thuoc,
            "the_cho": the_cho,
            "nhung": _nhung(request),
            # Màn hẹp / khung nổi chỉ hiện một cột: ?moi=1 (hoặc form lỗi) mở khung hỏi mới.
            "hoi_moi": (
                request.GET.get("moi") == "1"
                or form.is_bound
                or don_nhap is not None
                or thuoc is not None
            ),
            "goi_y_tu_van": GOI_Y_TU_VAN,
            "goi_y_ve_don": GOI_Y_VE_DON,
        },
    )


@xframe_options_sameorigin
@yeu_cau_vai_tro("khach_hang")
@require_http_methods(["GET", "POST"])
def danh_sach(request):
    """Hộp thư. POST gửi tin tới nhà thuốc đã chọn: đã từng nhắn thì nối vào cuộc trò chuyện cũ.

    GET ?thuoc=<mã> (từ trang sản phẩm) hoặc ?chi_nhanh=<mã> (từ trang chi nhánh): nếu đã có cuộc
    trò chuyện với nhà thuốc đó thì mở thẳng, thẻ sản phẩm chờ sẵn ở khung soạn tin.
    """
    thuoc = _thuoc_dang_hoi(request)
    if request.method == "POST":
        form = MoPhongForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                phong = bat_dau_tro_chuyen(
                    request.user,
                    form.cleaned_data["chi_nhanh"],
                    form.cleaned_data["noi_dung"],
                    cac_anh=form.cleaned_data["cac_anh"],
                    thuoc=thuoc,
                )
            except ValidationError as loi:
                form.add_error(None, loi)
            else:
                return _toi_phong(request, phong)
        return _hien_thi(request, form=form, thuoc=thuoc)
    if request.GET.get("moi") != "1":
        ma = request.GET.get("chi_nhanh", "")[:32]
        cac_phong = lay_cac_phong(request.user)
        if ma:
            phong = cac_phong.filter(chi_nhanh__ma_chi_nhanh=ma).first()
        elif thuoc is not None:
            # Hỏi về sản phẩm: mặc định nhắn nhà thuốc vừa trò chuyện gần nhất.
            phong = cac_phong.order_by("-tin_cuoi_id").first()
        else:
            phong = None
        if phong is not None:
            return _toi_phong(request, phong, **({"thuoc": thuoc.ma_thuoc} if thuoc else {}))
    return _hien_thi(request, thuoc=thuoc)


@xframe_options_sameorigin
@yeu_cau_vai_tro("khach_hang")
@require_GET
def chi_tiet(request, ma):
    phong = get_object_or_404(lay_cac_phong(request.user), pk=ma)
    return _hien_thi(request, phong=phong, thuoc=_thuoc_dang_hoi(request))


@xframe_options_sameorigin
@yeu_cau_vai_tro("khach_hang")
@require_http_methods(["GET", "POST"])
def tu_don_hang(request, ma):
    """Nút "Nhắn nhà thuốc về đơn này": đã từng trò chuyện với chi nhánh của đơn thì mở cuộc đó,
    thẻ đơn chờ sẵn ở khung soạn tin; chưa thì soạn tin đầu (không phải chọn chi nhánh)."""
    don = get_object_or_404(
        DonHang.objects.select_related("chi_nhanh"), pk=ma, khach_hang=request.user
    )
    phong = phong_cua_don(request.user, don)
    if phong is not None:
        return _toi_phong(request, phong, don=don.pk)
    form_don = TinDauVeDonForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form_don.is_valid():
        try:
            phong = bat_dau_ve_don(
                request.user,
                don,
                form_don.cleaned_data["noi_dung"],
                cac_anh=form_don.cleaned_data["cac_anh"],
            )
        except ValidationError as loi:
            form_don.add_error(None, loi)
        else:
            return _toi_phong(request, phong)
    return _hien_thi(request, don_nhap=don, form_don=form_don)


@yeu_cau_vai_tro("khach_hang")
@require_POST
def gui_tin(request, ma):
    """Gửi tin kèm ảnh trong cuộc trò chuyện đang mở."""
    phong = get_object_or_404(lay_cac_phong(request.user), pk=ma)
    return gui_tin_kem_anh(request, phong)


@yeu_cau_vai_tro("khach_hang")
@require_GET
def anh(request, ma):
    return xem_anh(request, ma)


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
