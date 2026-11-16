"""Khu quản lý: nhân viên chi nhánh xử lý đơn đặt giữ của chi nhánh mình."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.chung.loc_danh_sach import BoLoc, o_khoang_thoi_gian
from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen
from ung_dung.kho.loc import o_chi_nhanh
from ung_dung.tro_chuyen.selectors import phong_cua_don

from ..forms import XuLyDonForm
from ..models import PHUONG_THUC_TAI_QUAY, TRANG_THAI_DON, PhieuBan, YeuCauXuatHoaDon
from ..selectors import (
    dem_don_theo_trang_thai,
    lay_chi_tiet_don,
    lay_don,
    lay_lich_su,
    thong_tin_han,
    tim_don,
)
from ..services import don_hang as dich_vu
from ..services.giu_hang import don_giu_tren_lo_hong, kha_nang_dap_ung
from ..services.phieu_ban import ban_tai_quay
from ..services.trang_thai import CHUYEN_HOP_LE, NHAN_SU
from .khach_don_hang import tien_trinh

# hành động -> (trạng thái đích, nhãn nút, cần lý do, thao tác phụ)
HANH_DONG = {
    "nhan_tai_quay": ("hoan_thanh", "Khách đã nhận hàng và thanh toán", False, False),
    "huy": ("da_huy", "Hủy đơn", True, True),
}


def cac_hanh_dong(don, nguoi):
    if not co_quyen(nguoi, "don_hang.xu_ly"):
        return []
    qua_han = bool(getattr(don, "qua_han_giu", False))
    ket_qua = []
    for ma, (den, nhan, can_ly_do, phu) in HANH_DONG.items():
        if NHAN_SU not in CHUYEN_HOP_LE.get((don.trang_thai, den), set()):
            continue
        if ma == "nhan_tai_quay" and qua_han:
            continue  # quá hạn giữ: trang hiện hướng dẫn thay cho nút chính
        ket_qua.append({"ma": ma, "nhan": nhan, "can_ly_do": can_ly_do, "phu": phu})
    return ket_qua


@yeu_cau_quyen("don_hang.xem")
def danh_sach(request):
    # Trạng thái chọn bằng thẻ phía trên (kèm số đơn); các tiêu chí còn lại nằm trên thanh lọc chung.
    trang_thai = request.GET.get("trang_thai", "")
    if trang_thai not in dict(TRANG_THAI_DON):
        trang_thai = ""
    loc = BoLoc(
        request,
        ham_tim=tim_don,
        nhan_tim="Mã đơn khách đọc, tên hoặc số điện thoại",
        cac_o_chon=[
            *o_chi_nhanh(request.user, "chi_nhanh_id"),
            o_khoang_thoi_gian("thoi_diem_tao", "Đặt trong"),
        ],
    )
    dem = dem_don_theo_trang_thai(request.user)
    tap_hop = lay_don(request.user, trang_thai=trang_thai).annotate(
        so_mat_hang=Count("cac_dong", distinct=True)
    )
    loc_lo_hong = request.GET.get("giu_lo_hong") == "1"
    if loc_lo_hong:
        tap_hop = tap_hop.filter(pk__in=don_giu_tren_lo_hong().values("pk"))
    return render(
        request,
        "ban_hang/don_hang_danh_sach.html",
        {
            **loc.ngu_canh(tap_hop),
            "trang_thai": trang_thai,
            "cac_trang_thai": [(ma, nhan, dem.get(ma, 0)) for ma, nhan in TRANG_THAI_DON],
            "tong_so": sum(dem.values()),
            "loc_lo_hong": loc_lo_hong,
        },
    )


@yeu_cau_quyen("don_hang.xem")
def chi_tiet(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    cac_dong = lay_chi_tiet_don(don)
    hanh_dong = cac_hanh_dong(don, request.user)
    return render(
        request,
        "ban_hang/don_hang_chi_tiet.html",
        {
            "don": don,
            "cac_dong": cac_dong,
            "cac_lich_su": lay_lich_su(don),
            "tien_trinh": tien_trinh(don),
            "phieu_ban": PhieuBan.objects.filter(don_hang=don).first(),
            "yeu_cau_hoa_don": YeuCauXuatHoaDon.objects.filter(don_hang=don).first(),
            "cac_hanh_dong": hanh_dong,
            "duoc_chat": co_quyen(request.user, "tro_chuyen.dung"),
            "phong_chat": (
                phong_cua_don(request.user, don)
                if co_quyen(request.user, "tro_chuyen.dung")
                else None
            ),
            "co_hanh_dong_phu": any(hd["phu"] for hd in hanh_dong),
            "co_ke_don": any(dong.thuoc.la_thuoc_ke_don for dong in cac_dong),
            "duoc_ban_ke_don": co_quyen(request.user, "thuoc_ke_don.ban"),
            "phuong_thuc_tai_quay": PHUONG_THUC_TAI_QUAY,
            "han": thong_tin_han(don),
            "canh_bao_giu": kha_nang_dap_ung(don),
        },
    )


@require_POST
@yeu_cau_quyen("don_hang.xu_ly")
def xu_ly(request, ma, hanh_dong):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    form = XuLyDonForm(request.POST)
    if not form.is_valid():
        for loi in form.errors.values():
            messages.error(request, " ".join(loi))
        return redirect("ban_hang:don_hang_chi_tiet", ma=ma)
    try:
        if hanh_dong == "nhan_tai_quay":
            phieu = ban_tai_quay(
                request.user,
                don.chi_nhanh,
                [],
                don_hang=don,
                don_thuoc=form.don_thuoc(),
                phuong_thuc_thanh_toan=form.cleaned_data.get("phuong_thuc_thanh_toan")
                or "tien_mat",
            )
            messages.success(
                request, f"Đã giao đơn cho khách và lập phiếu bán {phieu.ma_phieu_ban}."
            )
        elif hanh_dong == "huy":
            dich_vu.huy_don(request.user, don, form.cleaned_data.get("ly_do", ""))
            messages.success(request, f"Đã hủy đơn {don.ma_don_hang}, hàng giữ đã được nhả.")
        else:
            messages.error(request, "Thao tác không hợp lệ.")
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    except PermissionDenied as loi:
        messages.error(request, str(loi) or "Bạn không có quyền thực hiện thao tác này.")
    return redirect("ban_hang:don_hang_chi_tiet", ma=ma)
