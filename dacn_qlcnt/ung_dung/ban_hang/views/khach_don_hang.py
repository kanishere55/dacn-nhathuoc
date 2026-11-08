from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from ung_dung.chung.permissions import yeu_cau_vai_tro

from ..forms import XuLyDonForm
from ..models import TRANG_THAI_DON
from ..selectors import lay_chi_tiet_don, lay_don, lay_lich_su
from ..services.don_hang import huy_don
from ..services.trang_thai import CHUYEN_HOP_LE, KHACH

NHOM_TRANG_THAI = {
    "": ("Tất cả", None),
    "dang_xu_ly": (
        "Đang xử lý",
        ["cho_thanh_toan", "cho_xac_nhan", "dang_giu", "dang_chuan_bi", "dang_giao"],
    ),
    "hoan_thanh": ("Hoàn thành", ["hoan_thanh"]),
    "da_huy": ("Đã hủy, hết hạn", ["da_huy", "het_han", "giao_that_bai"]),
}
# Các bước hiển thị trên thanh tiến trình theo hình thức nhận.
BUOC = {
    "giao_hang": ["cho_xac_nhan", "dang_chuan_bi", "dang_giao", "hoan_thanh"],
    "nhan_tai_quay": ["dang_giu", "hoan_thanh"],
}


@yeu_cau_vai_tro("khach_hang")
@require_GET
def danh_sach(request):
    nhom = request.GET.get("nhom", "")
    nhom = nhom if nhom in NHOM_TRANG_THAI else ""
    cac_don = lay_don(request.user).prefetch_related("cac_dong__thuoc")
    if NHOM_TRANG_THAI[nhom][1]:
        cac_don = cac_don.filter(trang_thai__in=NHOM_TRANG_THAI[nhom][1])
    return render(
        request,
        "ban_hang/khach/don_hang_danh_sach.html",
        {
            "trang": Paginator(cac_don, 10).get_page(request.GET.get("page")),
            "nhom": nhom,
            "cac_nhom": [(ma, nhan) for ma, (nhan, _) in NHOM_TRANG_THAI.items()],
        },
    )


def tien_trinh(don):
    """Danh sách (nhãn, đã qua, hiện tại) cho thanh tiến trình của đơn."""
    nhan = dict(TRANG_THAI_DON)
    cac_buoc = BUOC[don.hinh_thuc_nhan]
    if don.trang_thai == "cho_thanh_toan":
        cac_buoc = ["cho_thanh_toan", *cac_buoc]
    if don.trang_thai not in cac_buoc:
        return []
    vi_tri = cac_buoc.index(don.trang_thai)
    return [(nhan[buoc], so <= vi_tri, so == vi_tri) for so, buoc in enumerate(cac_buoc)]


@yeu_cau_vai_tro("khach_hang")
@require_GET
def chi_tiet(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    cac_dong = lay_chi_tiet_don(don)
    return render(
        request,
        "ban_hang/khach/don_hang_chi_tiet.html",
        {
            "don": don,
            "cac_dong": cac_dong,
            "co_ke_don": any(dong.thuoc.la_thuoc_ke_don for dong in cac_dong),
            "cac_lich_su": lay_lich_su(don),
            "tien_trinh": tien_trinh(don),
            "duoc_huy": not don.qua_han_giu
            and KHACH in CHUYEN_HOP_LE.get((don.trang_thai, "da_huy"), set()),
            "form_huy": XuLyDonForm(),
        },
    )


@yeu_cau_vai_tro("khach_hang")
@require_POST
def huy(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    form = XuLyDonForm(request.POST)
    form.is_valid()
    try:
        huy_don(request.user, don, form.cleaned_data.get("ly_do", ""))
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    else:
        messages.success(request, f"Đã hủy đơn {don.ma_don_hang}.")
    return redirect("ban_hang:khach_don_hang_chi_tiet", ma=don.pk)
