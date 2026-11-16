from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from ung_dung.ban_hang.forms import ThemThuocVaoGioForm
from ung_dung.chung.permissions import co_vai_tro, yeu_cau_vai_tro
from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import AnhChiNhanh, AnhThuoc, DanhGiaChiNhanh, DanhGiaThuoc
from ..selectors import (
    SAP_XEP_THUOC,
    lay_chi_nhanh_cong_khai,
    lay_danh_muc_san_pham_cong_khai,
    lay_nhom_thuoc_cong_khai,
    lay_thuoc_cong_khai,
)
from ..services.danh_gia import (
    da_mua,
    da_mua_tai_chi_nhanh,
    luu_danh_gia,
    luu_danh_gia_chi_nhanh,
    tom_tat_danh_gia,
    tom_tat_danh_gia_chi_nhanh,
)


def la_khach(nguoi):
    return co_vai_tro(nguoi, "khach_hang")


TEN_SAP_XEP = {
    "ten": "Tên A–Z",
    "gia_tang": "Giá thấp đến cao",
    "gia_giam": "Giá cao đến thấp",
    "giam_nhieu": "Giảm giá nhiều",
}


@require_GET
def danh_sach_thuoc(request):
    bo_loc = {
        "tu_khoa": cat_khoang_trang(request.GET.get("q", ""))[:150],
        "ma_nhom": request.GET.get("nhom", "")[:32],
        "ma_danh_muc": request.GET.get("danh_muc", "")[:32],
        "khong_ke_don": request.GET.get("khong_ke_don") == "1",
        "dang_giam": request.GET.get("dang_giam") == "1",
        "sap_xep": request.GET.get("sap_xep", "ten")
        if request.GET.get("sap_xep") in SAP_XEP_THUOC
        else "ten",
    }
    cac_thuoc = lay_thuoc_cong_khai(
        bo_loc["tu_khoa"],
        bo_loc["ma_nhom"],
        ma_danh_muc=bo_loc["ma_danh_muc"],
        khong_ke_don=bo_loc["khong_ke_don"],
        dang_giam=bo_loc["dang_giam"],
        sap_xep=bo_loc["sap_xep"],
    )
    cac_danh_muc = list(lay_danh_muc_san_pham_cong_khai())
    return render(
        request,
        "danh_muc/khach/danh_sach_thuoc.html",
        {
            "trang": Paginator(cac_thuoc, 12).get_page(request.GET.get("page")),
            "bo_loc": bo_loc,
            "cac_nhom": lay_nhom_thuoc_cong_khai(),
            "cac_danh_muc": cac_danh_muc,
            "danh_muc_chon": next(
                (dm for dm in cac_danh_muc if dm.ma_danh_muc_san_pham == bo_loc["ma_danh_muc"]),
                None,
            ),
            "ten_sap_xep": TEN_SAP_XEP,
        },
    )


@require_GET
def chi_tiet_thuoc(request, ma):
    thuoc = get_object_or_404(lay_thuoc_cong_khai(), ma_thuoc=ma)
    cac_anh = AnhThuoc.objects.filter(thuoc=thuoc).defer("noi_dung_anh")
    cung_danh_muc = (
        lay_thuoc_cong_khai(ma_danh_muc=thuoc.danh_muc_san_pham.ma_danh_muc_san_pham).exclude(
            pk=thuoc.pk
        )[:4]
        if thuoc.danh_muc_san_pham_id
        else []
    )
    return render(
        request,
        "danh_muc/khach/chi_tiet_thuoc.html",
        {
            "thuoc": thuoc,
            "cac_anh": cac_anh,
            "cung_danh_muc": cung_danh_muc,
            "danh_gia": tom_tat_danh_gia(thuoc),
            "duoc_danh_gia": la_khach(request.user) and da_mua(request.user, thuoc),
            "danh_gia_cua_toi": DanhGiaThuoc.objects.filter(
                thuoc=thuoc, khach_hang_id=getattr(request.user, "pk", None)
            ).first(),
            "form_them": ThemThuocVaoGioForm(initial={"so_luong": 1}),
        },
    )


@require_GET
def chi_tiet_chi_nhanh(request, ma):
    chi_nhanh = get_object_or_404(lay_chi_nhanh_cong_khai(), ma_chi_nhanh=ma)
    return render(
        request,
        "danh_muc/khach/chi_tiet_chi_nhanh.html",
        {
            "chi_nhanh": chi_nhanh,
            "cac_anh": AnhChiNhanh.objects.filter(chi_nhanh=chi_nhanh).defer("noi_dung_anh"),
            "danh_gia": tom_tat_danh_gia_chi_nhanh(chi_nhanh),
            "duoc_danh_gia": la_khach(request.user)
            and da_mua_tai_chi_nhanh(request.user, chi_nhanh),
            "danh_gia_cua_toi": DanhGiaChiNhanh.objects.filter(
                chi_nhanh=chi_nhanh, khach_hang_id=getattr(request.user, "pk", None)
            ).first(),
        },
    )


@require_POST
@yeu_cau_vai_tro("khach_hang")
def danh_gia_thuoc(request, ma):
    thuoc = get_object_or_404(lay_thuoc_cong_khai(), ma_thuoc=ma)
    try:
        luu_danh_gia(
            request.user, thuoc, request.POST.get("so_sao", 0), request.POST.get("noi_dung", "")
        )
    except (ValidationError, ValueError) as loi:
        messages.error(request, " ".join(getattr(loi, "messages", [str(loi)])))
    else:
        messages.success(request, "Cảm ơn bạn đã đánh giá.")
    return redirect(reverse("danh_muc:khach_thuoc_chi_tiet", args=[ma]) + "#danh-gia")


@require_POST
@yeu_cau_vai_tro("khach_hang")
def danh_gia_chi_nhanh(request, ma):
    chi_nhanh = get_object_or_404(lay_chi_nhanh_cong_khai(), ma_chi_nhanh=ma)
    try:
        luu_danh_gia_chi_nhanh(
            request.user, chi_nhanh, request.POST.get("so_sao", 0), request.POST.get("noi_dung", "")
        )
    except (ValidationError, ValueError) as loi:
        messages.error(request, " ".join(getattr(loi, "messages", [str(loi)])))
    else:
        messages.success(request, "Cảm ơn bạn đã đánh giá chi nhánh.")
    return redirect(reverse("danh_muc:khach_chi_nhanh_chi_tiet", args=[ma]) + "#danh-gia")
