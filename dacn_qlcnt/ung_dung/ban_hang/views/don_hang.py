"""Khu quản lý: nhân viên chi nhánh xử lý đơn của chi nhánh mình."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.chung.permissions import (
    NHAN_SU_CHI_NHANH,
    NHAN_SU_CHUOI,
    co_vai_tro,
    yeu_cau_vai_tro,
)

from ..forms import XuLyDonForm
from ..models import HINH_THUC_NHAN, TRANG_THAI_DON, PhieuBan
from ..selectors import dem_don_theo_trang_thai, lay_chi_tiet_don, lay_don, lay_lich_su
from ..services import don_hang as dich_vu
from ..services.phieu_ban import ban_tai_quay
from ..services.trang_thai import CHUYEN_HOP_LE, NHAN_SU
from .khach_don_hang import tien_trinh

# hành động -> (trạng thái đích, nhãn nút, cần lý do)
HANH_DONG = {
    "nhan_tai_quay": ("hoan_thanh", "Khách đã nhận và thanh toán tại quầy", False),
    "xac_nhan": ("dang_chuan_bi", "Xác nhận đơn và xuất kho", False),
    "giao_van_chuyen": ("dang_giao", "Đã giao cho người vận chuyển", False),
    "da_giao": ("hoan_thanh", "Khách đã nhận hàng", False),
    "giao_that_bai": ("giao_that_bai", "Giao không thành công", True),
    "huy": ("da_huy", "Hủy đơn", True),
}


def cac_hanh_dong(don):
    ket_qua = []
    for ma, (den, nhan, can_ly_do) in HANH_DONG.items():
        if NHAN_SU not in CHUYEN_HOP_LE.get((don.trang_thai, den), set()):
            continue
        if ma == "nhan_tai_quay" and don.hinh_thuc_nhan != "nhan_tai_quay":
            continue
        if ma == "da_giao" and don.hinh_thuc_nhan != "giao_hang":
            continue
        ket_qua.append({"ma": ma, "nhan": nhan, "can_ly_do": can_ly_do})
    return ket_qua


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def danh_sach(request):
    bo_loc = {
        "trang_thai": request.GET.get("trang_thai", ""),
        "hinh_thuc_nhan": request.GET.get("hinh_thuc_nhan", ""),
        "tim": request.GET.get("tim", "").strip()[:60],
    }
    if bo_loc["trang_thai"] not in dict(TRANG_THAI_DON):
        bo_loc["trang_thai"] = ""
    if bo_loc["hinh_thuc_nhan"] not in dict(HINH_THUC_NHAN):
        bo_loc["hinh_thuc_nhan"] = ""
    dem = dem_don_theo_trang_thai(request.user)
    return render(
        request,
        "ban_hang/don_hang_danh_sach.html",
        {
            "trang": Paginator(lay_don(request.user, **bo_loc), 25).get_page(
                request.GET.get("page")
            ),
            "bo_loc": bo_loc,
            "cac_trang_thai": [(ma, nhan, dem.get(ma, 0)) for ma, nhan in TRANG_THAI_DON],
            "tong_so": sum(dem.values()),
            "cac_hinh_thuc": HINH_THUC_NHAN,
        },
    )


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def chi_tiet(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    cac_dong = lay_chi_tiet_don(don)
    return render(
        request,
        "ban_hang/don_hang_chi_tiet.html",
        {
            "don": don,
            "cac_dong": cac_dong,
            "cac_lich_su": lay_lich_su(don),
            "tien_trinh": tien_trinh(don),
            "phieu_ban": PhieuBan.objects.filter(don_hang=don).first(),
            "cac_hanh_dong": (
                cac_hanh_dong(don) if co_vai_tro(request.user, *NHAN_SU_CHI_NHANH) else []
            ),
            "co_ke_don": any(dong.thuoc.la_thuoc_ke_don for dong in cac_dong),
        },
    )


@require_POST
@yeu_cau_vai_tro(*NHAN_SU_CHI_NHANH)
def xu_ly(request, ma, hanh_dong):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    form = XuLyDonForm(request.POST)
    form.is_valid()
    ly_do = form.cleaned_data.get("ly_do", "")
    try:
        if hanh_dong == "nhan_tai_quay":
            phieu = ban_tai_quay(
                request.user,
                don.chi_nhanh,
                [],
                don_hang=don,
                da_kiem_tra_don_thuoc=form.cleaned_data.get("da_kiem_tra_don_thuoc", False),
            )
            messages.success(request, f"Đã lập phiếu bán {phieu.ma_phieu_ban}.")
        elif hanh_dong == "xac_nhan":
            phieu = dich_vu.xac_nhan_don(request.user, don)
            messages.success(request, f"Đã xác nhận đơn, phiếu bán {phieu.ma_phieu_ban}.")
        elif hanh_dong == "giao_van_chuyen":
            dich_vu.giao_cho_van_chuyen(request.user, don)
        elif hanh_dong == "da_giao":
            dich_vu.xac_nhan_da_giao(request.user, don)
        elif hanh_dong == "giao_that_bai":
            dich_vu.bao_giao_that_bai(request.user, don, ly_do)
        elif hanh_dong == "huy":
            dich_vu.huy_don(request.user, don, ly_do)
        else:
            messages.error(request, "Thao tác không hợp lệ.")
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    return redirect("ban_hang:don_hang_chi_tiet", ma=ma)
