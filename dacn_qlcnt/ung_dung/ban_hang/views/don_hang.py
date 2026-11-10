"""Khu quản lý: nhân viên chi nhánh xử lý đơn của chi nhánh mình."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.chung.loc_danh_sach import BoLoc, OChon, o_khoang_thoi_gian
from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen
from ung_dung.kho.loc import o_chi_nhanh
from ung_dung.thanh_toan.selectors import giao_dich_cua_don
from ung_dung.thanh_toan.services.cong import hoan_tien, xac_nhan_tay
from ung_dung.tro_chuyen.selectors import phong_cua_don

from ..forms import PHUONG_THUC_TAI_QUAY, XuLyDonForm
from ..models import (
    HINH_THUC_NHAN,
    PHUONG_THUC_THANH_TOAN,
    TRANG_THAI_DON,
    PhieuBan,
    YeuCauXuatHoaDon,
)
from ..selectors import dem_don_theo_trang_thai, lay_chi_tiet_don, lay_don, lay_lich_su
from ..services import don_hang as dich_vu
from ..services.phieu_ban import ban_tai_quay
from ..services.trang_thai import CHUYEN_HOP_LE, NHAN_SU
from .khach_don_hang import tien_trinh

# hành động -> (trạng thái đích, nhãn nút, cần lý do)
HANH_DONG = {
    "xac_nhan_thanh_toan": ("cho_xac_nhan", "Đã nhận đủ tiền khách chuyển", False),
    "nhan_tai_quay": ("hoan_thanh", "Khách đã nhận và thanh toán tại quầy", False),
    "xac_nhan": ("dang_chuan_bi", "Xác nhận đơn và xuất kho", False),
    "giao_van_chuyen": ("dang_giao", "Đã giao cho người vận chuyển", False),
    "giao_that_bai": ("giao_that_bai", "Giao không thành công", True),
    "huy": ("da_huy", "Hủy đơn", True),
}


def cac_hanh_dong(don, nguoi):
    ket_qua = []
    for ma, (den, nhan, can_ly_do) in HANH_DONG.items():
        if NHAN_SU not in CHUYEN_HOP_LE.get((don.trang_thai, den), set()):
            continue
        if ma == "nhan_tai_quay" and don.hinh_thuc_nhan != "nhan_tai_quay":
            continue
        # Hủy và báo giao thất bại là thao tác phụ: gom riêng để không bấm nhầm.
        ket_qua.append(
            {"ma": ma, "nhan": nhan, "can_ly_do": can_ly_do, "phu": ma in ("huy", "giao_that_bai")}
        )
    if don.trang_thai_thanh_toan == "cho_hoan_tien" and co_quyen(nguoi, "don_hang.hoan_tien"):
        ket_qua.append({"ma": "hoan_tien", "nhan": "Đã hoàn tiền cho khách", "can_ly_do": False})
    return ket_qua


@yeu_cau_quyen("don_hang.xem")
def danh_sach(request):
    # Trạng thái chọn bằng thẻ phía trên (kèm số đơn); các tiêu chí còn lại nằm trên thanh lọc chung.
    trang_thai = request.GET.get("trang_thai", "")
    if trang_thai not in dict(TRANG_THAI_DON):
        trang_thai = ""
    loc = BoLoc(
        request,
        cac_cot_tim=(
            "ma_don_hang",
            "khach_hang__ten_dang_nhap",
            "khach_hang__ho_ten",
            "so_dien_thoai_nhan",
        ),
        nhan_tim="Mã đơn, khách, số điện thoại",
        cac_o_chon=[
            OChon("hinh_thuc_nhan", "Hình thức", HINH_THUC_NHAN, "hinh_thuc_nhan"),
            OChon("thanh_toan", "Thanh toán", PHUONG_THUC_THANH_TOAN, "phuong_thuc_thanh_toan"),
            *o_chi_nhanh(request.user, "chi_nhanh_id"),
            o_khoang_thoi_gian("thoi_diem_tao", "Đặt trong"),
        ],
    )
    dem = dem_don_theo_trang_thai(request.user)
    return render(
        request,
        "ban_hang/don_hang_danh_sach.html",
        {
            **loc.ngu_canh(lay_don(request.user, trang_thai=trang_thai)),
            "trang_thai": trang_thai,
            "cac_trang_thai": [(ma, nhan, dem.get(ma, 0)) for ma, nhan in TRANG_THAI_DON],
            "tong_so": sum(dem.values()),
        },
    )


@yeu_cau_quyen("don_hang.xem")
def chi_tiet(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    cac_dong = lay_chi_tiet_don(don)
    hanh_dong = (
        cac_hanh_dong(don, request.user)
        if co_quyen(request.user, "don_hang.xu_ly", "don_hang.hoan_tien")
        else []
    )
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
            "co_hanh_dong_phu": any(hd.get("phu") for hd in hanh_dong),
            "co_ke_don": any(dong.thuoc.la_thuoc_ke_don for dong in cac_dong),
            "cac_giao_dich": giao_dich_cua_don(don),
            "phuong_thuc_tai_quay": PHUONG_THUC_TAI_QUAY,
            "han_tu_hoan_thanh": (
                dich_vu.han_tu_hoan_thanh(don) if don.trang_thai == "dang_giao" else None
            ),
        },
    )


@require_POST
@yeu_cau_quyen("don_hang.xu_ly", "don_hang.hoan_tien")
def xu_ly(request, ma, hanh_dong):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    form = XuLyDonForm(request.POST)
    if not form.is_valid():
        for loi in form.errors.values():
            messages.error(request, " ".join(loi))
        return redirect("ban_hang:don_hang_chi_tiet", ma=ma)
    ly_do = form.cleaned_data.get("ly_do", "")
    try:
        if hanh_dong == "xac_nhan_thanh_toan":
            xac_nhan_tay(request.user, don, form.cleaned_data.get("ma_tham_chieu", ""))
            messages.success(request, "Đã ghi nhận thanh toán, đơn chuyển chờ xác nhận.")
        elif hanh_dong == "hoan_tien":
            hoan_tien(
                request.user,
                don,
                phuong_thuc=form.cleaned_data.get("phuong_thuc_hoan") or "chuyen_khoan",
                ma_tham_chieu=form.cleaned_data.get("ma_tham_chieu", ""),
            )
            messages.success(request, "Đã ghi nhận hoàn tiền.")
        elif hanh_dong == "nhan_tai_quay":
            phieu = ban_tai_quay(
                request.user,
                don.chi_nhanh,
                [],
                don_hang=don,
                don_thuoc=form.don_thuoc(),
                phuong_thuc_thanh_toan=form.cleaned_data.get("phuong_thuc_thanh_toan")
                or "tien_mat",
            )
            messages.success(request, f"Đã lập phiếu bán {phieu.ma_phieu_ban}.")
        elif hanh_dong == "xac_nhan":
            phieu = dich_vu.xac_nhan_don(request.user, don)
            messages.success(request, f"Đã xác nhận đơn, phiếu bán {phieu.ma_phieu_ban}.")
        elif hanh_dong == "giao_van_chuyen":
            dich_vu.giao_cho_van_chuyen(request.user, don)
        elif hanh_dong == "giao_that_bai":
            dich_vu.bao_giao_that_bai(request.user, don, ly_do)
        elif hanh_dong == "huy":
            dich_vu.huy_don(request.user, don, ly_do)
        else:
            messages.error(request, "Thao tác không hợp lệ.")
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    return redirect("ban_hang:don_hang_chi_tiet", ma=ma)
