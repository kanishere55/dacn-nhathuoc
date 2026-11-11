"""Khu quản lý: nhân viên chi nhánh xử lý đơn của chi nhánh mình."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ung_dung.chung.loc_danh_sach import BoLoc, OChon, o_khoang_thoi_gian
from ung_dung.chung.permissions import co_quyen, thay_toan_chuoi, yeu_cau_quyen
from ung_dung.kho.loc import o_chi_nhanh
from ung_dung.thanh_toan.models import GiaoDichThanhToan
from ung_dung.thanh_toan.selectors import giao_dich_cua_don
from ung_dung.thanh_toan.services.cong import (
    LOI_BAO_NHAN_TIEN,
    da_thu_tien_cod,
    hoan_tien,
    xac_nhan_tay,
)
from ung_dung.thanh_toan.services.doi_soat import doi_soat
from ung_dung.tro_chuyen.selectors import phong_cua_don

from ..forms import PHUONG_THUC_TAI_QUAY, XuLyDonForm
from ..models import (
    HINH_THUC_NHAN,
    PHUONG_THUC_THANH_TOAN,
    TRANG_THAI_DON,
    PhieuBan,
    YeuCauXuatHoaDon,
)
from ..selectors import (
    dem_don_theo_trang_thai,
    don_cho_doi_soat_cod,
    don_cho_hoan_tien,
    lay_chi_tiet_don,
    lay_don,
    lay_lich_su,
    lay_lo_da_xuat,
    thong_tin_han,
    tim_don,
)
from ..services import don_hang as dich_vu
from ..services.giu_hang import don_giu_tren_lo_hong, kha_nang_dap_ung
from ..services.phieu_ban import ban_tai_quay
from ..services.trang_thai import CHUYEN_HOP_LE, NHAN_SU
from .khach_don_hang import tien_trinh

# hành động -> (trạng thái đích, nhãn nút, cần lý do)
HANH_DONG = {
    "xac_nhan_thanh_toan": ("cho_xac_nhan", "Ghi nhận tiền khách chuyển theo sao kê", False),
    "nhan_tai_quay": ("hoan_thanh", "Khách đã nhận và thanh toán tại quầy", False),
    "xac_nhan": ("dang_chuan_bi", "Xác nhận đơn và xuất kho", False),
    "giao_van_chuyen": ("dang_giao", "Đã giao cho người vận chuyển", False),
    "xac_nhan_giao_thanh_cong": ("hoan_thanh", "Xác nhận đã giao thành công", True),
    "giao_that_bai": ("giao_that_bai", "Giao không thành công", True),
    "huy": ("da_huy", "Hủy đơn", True),
}
# Bộ lọc nhanh việc về tiền trên danh sách đơn.
LOC_TIEN = {
    "doi_soat_cod": ("Cần đối soát COD", don_cho_doi_soat_cod),
    "cho_hoan_tien": ("Chờ hoàn tiền", don_cho_hoan_tien),
}


def cac_hanh_dong(don, nguoi):
    ket_qua = []
    qua_han = bool(getattr(don, "qua_han_giu", False))
    for ma, (den, nhan, can_ly_do) in HANH_DONG.items():
        if NHAN_SU not in CHUYEN_HOP_LE.get((don.trang_thai, den), set()):
            continue
        if ma == "nhan_tai_quay" and don.hinh_thuc_nhan != "nhan_tai_quay":
            continue
        if ma == "xac_nhan_giao_thanh_cong" and don.trang_thai != "dang_giao":
            continue  # đơn giữ tại quầy hoàn thành bằng "Khách đã nhận", không qua đối chiếu giao nhận
        if ma in ("nhan_tai_quay", "xac_nhan") and qua_han:
            continue  # quá hạn giữ: trang hiện hướng dẫn thay cho nút chính
        if ma == "xac_nhan_thanh_toan" and (
            don.phuong_thuc_thanh_toan != "chuyen_khoan"
            or not co_quyen(nguoi, "thanh_toan.xac_nhan")
        ):
            continue
        if ma != "xac_nhan_thanh_toan" and not co_quyen(nguoi, "don_hang.xu_ly"):
            continue
        # Hủy và báo giao thất bại là thao tác phụ: gom riêng để không bấm nhầm.
        ket_qua.append(
            {"ma": ma, "nhan": nhan, "can_ly_do": can_ly_do, "phu": ma in ("huy", "giao_that_bai")}
        )
    if (
        co_quyen(nguoi, "thanh_toan.xac_nhan")
        and GiaoDichThanhToan.objects.filter(
            don_hang=don, phuong_thuc="cod", trang_thai="cho"
        ).exists()
    ):
        ket_qua.append(
            {"ma": "da_thu_cod", "nhan": "Đã nhận tiền COD từ người giao", "can_ly_do": False}
        )
    if don.trang_thai_thanh_toan == "cho_hoan_tien" and co_quyen(nguoi, "don_hang.hoan_tien"):
        ket_qua.append({"ma": "hoan_tien", "nhan": "Đã hoàn tiền cho khách", "can_ly_do": False})
    return ket_qua


def _tim_don(tap_hop, tu_khoa):
    return tim_don(tap_hop, tu_khoa)


@yeu_cau_quyen("don_hang.xem")
def danh_sach(request):
    # Trạng thái chọn bằng thẻ phía trên (kèm số đơn); các tiêu chí còn lại nằm trên thanh lọc chung.
    trang_thai = request.GET.get("trang_thai", "")
    if trang_thai not in dict(TRANG_THAI_DON):
        trang_thai = ""
    loc_tien = request.GET.get("tien", "")
    if loc_tien not in LOC_TIEN:
        loc_tien = ""
    loc = BoLoc(
        request,
        ham_tim=_tim_don,
        nhan_tim="Mã đơn, tên khách, số điện thoại",
        cac_o_chon=[
            OChon("hinh_thuc_nhan", "Hình thức", HINH_THUC_NHAN, "hinh_thuc_nhan"),
            OChon("thanh_toan", "Thanh toán", PHUONG_THUC_THANH_TOAN, "phuong_thuc_thanh_toan"),
            *o_chi_nhanh(request.user, "chi_nhanh_id"),
            o_khoang_thoi_gian("thoi_diem_tao", "Đặt trong"),
        ],
    )
    dem = dem_don_theo_trang_thai(request.user)
    tap_hop = lay_don(request.user, trang_thai=trang_thai)
    if loc_tien:
        tap_hop = LOC_TIEN[loc_tien][1](tap_hop)
    loc_lo_hong = request.GET.get("giu_lo_hong") == "1"
    if loc_lo_hong:
        tap_hop = tap_hop.filter(pk__in=don_giu_tren_lo_hong().values("pk"))
    tat_ca = lay_don(request.user)
    return render(
        request,
        "ban_hang/don_hang_danh_sach.html",
        {
            **loc.ngu_canh(tap_hop),
            "trang_thai": trang_thai,
            "cac_trang_thai": [(ma, nhan, dem.get(ma, 0)) for ma, nhan in TRANG_THAI_DON],
            "tong_so": sum(dem.values()),
            "loc_tien": loc_tien,
            "cac_loc_tien": [
                (ma, nhan, ham(tat_ca).count()) for ma, (nhan, ham) in LOC_TIEN.items()
            ],
            "loc_lo_hong": loc_lo_hong,
            "duoc_xem_tien_chua_khop": thay_toan_chuoi(request.user)
            and co_quyen(request.user, "thanh_toan.xac_nhan"),
        },
    )


@yeu_cau_quyen("don_hang.xem")
def chi_tiet(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    cac_dong = lay_chi_tiet_don(don)
    hanh_dong = (
        cac_hanh_dong(don, request.user)
        if co_quyen(request.user, "don_hang.xu_ly", "don_hang.hoan_tien", "thanh_toan.xac_nhan")
        else []
    )
    co_ke_don = any(dong.thuoc.la_thuoc_ke_don for dong in cac_dong)
    han_doi_chieu = dich_vu.han_doi_chieu_giao(don) if don.trang_thai == "dang_giao" else None
    tien = doi_soat(don)
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
            "co_ke_don": co_ke_don,
            "duoc_ban_ke_don": co_quyen(request.user, "thuoc_ke_don.ban"),
            "cac_giao_dich": giao_dich_cua_don(don),
            "phuong_thuc_tai_quay": PHUONG_THUC_TAI_QUAY,
            "han_doi_chieu_giao": han_doi_chieu,
            "qua_han_doi_chieu": bool(han_doi_chieu and han_doi_chieu <= timezone.now()),
            "han": thong_tin_han(don),
            "tien": tien,
            "cod_cho_doi_soat": GiaoDichThanhToan.objects.filter(
                don_hang=don, phuong_thuc="cod", trang_thai="cho"
            ).first(),
            "canh_bao_giu": kha_nang_dap_ung(don),
            "duoc_hoan_tien": co_quyen(request.user, "don_hang.hoan_tien"),
            "duoc_huy_hang": co_quyen(request.user, "xuat_huy.tao"),
            "cac_lo_da_xuat": list(lay_lo_da_xuat(don)) if don.trang_thai == "dang_giao" else [],
        },
    )


def _bao_ket_qua_tien(request, ket_qua):
    loi_bao = LOI_BAO_NHAN_TIEN.get(ket_qua, LOI_BAO_NHAN_TIEN["da_ghi"])
    if ket_qua in ("xac_nhan", "da_ghi"):
        messages.success(request, loi_bao)
    else:
        messages.warning(request, loi_bao)


def _luong_giao_that_bai(du_lieu, don):
    cac_lo = {}
    for dong in lay_lo_da_xuat(don):
        so_luong = []
        for loai in ("hoan_kho", "da_huy", "that_lac"):
            so = du_lieu.get(f"{loai}_{dong.pk}", "").strip() or "0"
            if not so.isdecimal() or len(so) > 10:
                raise ValidationError("Số lượng xử lý theo lô phải là số nguyên không âm.")
            so_luong.append(int(so))
        cac_lo[dong.pk] = tuple(so_luong)
    return cac_lo


@require_POST
@yeu_cau_quyen("don_hang.xu_ly", "don_hang.hoan_tien", "thanh_toan.xac_nhan")
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
            ket_qua = xac_nhan_tay(
                request.user,
                don,
                form.cleaned_data.get("ma_tham_chieu", ""),
                so_tien=form.cleaned_data.get("so_tien_nhan"),
            )
            _bao_ket_qua_tien(request, ket_qua)
        elif hanh_dong == "da_thu_cod":
            dong = da_thu_tien_cod(request.user, don, ly_do)
            messages.success(
                request, f"Đã ghi nhận nhận {dong.so_tien:,.0f} đ tiền COD.".replace(",", ".")
            )
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
        elif hanh_dong == "xac_nhan_giao_thanh_cong":
            dich_vu.xac_nhan_giao_thanh_cong(request.user, don, ly_do)
            messages.success(request, "Đã xác nhận giao thành công.")
        elif hanh_dong == "giao_that_bai":
            cach_xu_ly = form.cleaned_data["xu_ly_hang_giao"]
            dich_vu.bao_giao_that_bai(
                request.user,
                don,
                ly_do,
                xu_ly_hang=cach_xu_ly,
                so_luong_theo_lo=(
                    _luong_giao_that_bai(request.POST, don) if cach_xu_ly == "theo_lo" else None
                ),
            )
            messages.success(request, "Đã ghi nhận giao thất bại và kết quả xử lý hàng.")
        elif hanh_dong == "huy":
            dich_vu.huy_don(request.user, don, ly_do)
        else:
            messages.error(request, "Thao tác không hợp lệ.")
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    except PermissionDenied as loi:
        messages.error(request, str(loi) or "Bạn không có quyền thực hiện thao tác này.")
    return redirect("ban_hang:don_hang_chi_tiet", ma=ma)
