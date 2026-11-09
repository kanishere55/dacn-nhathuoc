"""Khách đặt đơn: giữ hàng theo FEFO, chụp giá, ghi lịch sử và gửi email xác nhận."""

import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_vai_tro
from ung_dung.danh_muc.models import Thuoc
from ung_dung.danh_muc.selectors import them_gia_va_anh
from ung_dung.kho.services.giao_dich import khoa_kho, phan_bo_fefo
from ung_dung.thanh_toan.services.ghi import tao_cho

from ..models import ChiTietDonHang, DonHang, PhanBoDonHang
from .giao_hang import BAN_KINH_GIAO_MET, tinh_phi_giao
from .thong_bao_don import bao_don_moi
from .trang_thai import ghi_lich_su

GIO_GIU_TAI_QUAY = 24
GIO_CHO_XAC_NHAN = 24
PHUT_CHO_THANH_TOAN = 30
PHUONG_THUC_GIAO = ("cod", "chuyen_khoan", "momo")


# Bỏ 0, 1, I, L, O để khách đọc mã tại quầy hay gõ vào nội dung chuyển khoản không nhầm.
KY_TU_MA_DON = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def tao_ma_don(thoi_diem):
    """Mã đơn ngắn dạng DH + yymmdd + 5 ký tự, ví dụ DH261109K7M4Q."""
    ngay = timezone.localtime(thoi_diem).strftime("%y%m%d")
    for _ in range(8):
        ma = "DH" + ngay + "".join(secrets.choice(KY_TU_MA_DON) for _ in range(5))
        if not DonHang.objects.filter(ma_don_hang=ma).exists():
            return ma
    raise ValidationError("Chưa cấp được mã đơn, vui lòng thử lại.")


def gop_dong(cac_dong):
    yeu_cau = {}
    for dong in cac_dong:
        luong = dong["so_luong"]
        if isinstance(luong, bool) or not isinstance(luong, int) or luong <= 0:
            raise ValidationError("Số lượng phải là số nguyên dương.")
        yeu_cau[dong["thuoc"].pk] = yeu_cau.get(dong["thuoc"].pk, 0) + luong
    if not yeu_cau:
        raise ValidationError("Đơn cần ít nhất một thuốc.")
    return yeu_cau


@transaction.atomic
def dat_hang(
    nguoi,
    chi_nhanh,
    cac_dong,
    *,
    hinh_thuc_nhan="nhan_tai_quay",
    phuong_thuc_thanh_toan="tai_quay",
    giao=None,
    ghi_chu_khach="",
):
    """Tạo đơn trong một transaction đã khóa kho chi nhánh.

    `giao` (bắt buộc khi giao hàng): ten_nguoi_nhan, so_dien_thoai, dia_chi, vi_tri,
    khoang_cach_met. Quãng đường được tính trước khi gọi để không giữ khóa kho trong
    lúc chờ dịch vụ bản đồ.
    """
    kiem_tra_vai_tro(nguoi, "khach_hang")
    yeu_cau = gop_dong(cac_dong)
    giao_hang = hinh_thuc_nhan == "giao_hang"
    if giao_hang and phuong_thuc_thanh_toan not in PHUONG_THUC_GIAO:
        raise ValidationError("Phương thức thanh toán không dùng được cho đơn giao hàng.")
    if not giao_hang and phuong_thuc_thanh_toan != "tai_quay":
        raise ValidationError("Đơn nhận tại nhà thuốc thanh toán tại quầy.")
    khoa_kho(chi_nhanh)
    cac_thuoc = them_gia_va_anh(Thuoc.objects.filter(pk__in=yeu_cau, dang_hoat_dong=True)).in_bulk()
    if len(cac_thuoc) != len(yeu_cau):
        raise ValidationError("Có thuốc đã ngừng kinh doanh, hãy bỏ khỏi giỏ.")
    if giao_hang:
        ke_don = [t.ten_thuoc for t in cac_thuoc.values() if t.la_thuoc_ke_don]
        if ke_don:
            raise ValidationError(
                f"{', '.join(ke_don)} là thuốc kê đơn, không bán giao hàng. "
                "Hãy chọn nhận tại nhà thuốc và mang theo đơn thuốc."
            )
        if giao is None or giao["khoang_cach_met"] > BAN_KINH_GIAO_MET:
            raise ValidationError("Địa chỉ nằm ngoài phạm vi giao của chi nhánh.")

    bay_gio = timezone.now()
    if not giao_hang:
        trang_thai, han_giu = "dang_giu", timedelta(hours=GIO_GIU_TAI_QUAY)
    elif phuong_thuc_thanh_toan == "cod":
        trang_thai, han_giu = "cho_xac_nhan", timedelta(hours=GIO_CHO_XAC_NHAN)
    else:
        trang_thai, han_giu = "cho_thanh_toan", timedelta(minutes=PHUT_CHO_THANH_TOAN)
    don = DonHang(
        ma_don_hang=tao_ma_don(bay_gio),
        khach_hang=nguoi,
        chi_nhanh=chi_nhanh,
        hinh_thuc_nhan=hinh_thuc_nhan,
        trang_thai=trang_thai,
        phuong_thuc_thanh_toan=phuong_thuc_thanh_toan,
        thoi_diem_tao=bay_gio,
        thoi_diem_het_giu=bay_gio + han_giu,
        ghi_chu_khach=ghi_chu_khach,
    )
    if giao_hang:
        don.ten_nguoi_nhan = giao["ten_nguoi_nhan"]
        don.so_dien_thoai_nhan = giao["so_dien_thoai"]
        don.dia_chi_giao = giao["dia_chi"]
        don.vi_tri_giao = giao["vi_tri"]
        don.khoang_cach_met = giao["khoang_cach_met"]
        don.phi_giao_hang = tinh_phi_giao(giao["khoang_cach_met"])
    # Ràng buộc tổng = tiền hàng - giảm + phí đúng ngay từ lần lưu đầu (tiền hàng còn 0).
    don.tong_thanh_toan = don.phi_giao_hang
    don.save()

    tien_hang = 0
    for ma, luong in sorted(yeu_cau.items()):
        thuoc = cac_thuoc[ma]
        dong = ChiTietDonHang.objects.create(
            don_hang=don,
            thuoc=thuoc,
            so_luong=luong,
            gia_niem_yet=thuoc.gia_ban,
            phan_tram_giam=thuoc.phan_tram_giam,
            don_gia=thuoc.don_gia,
        )
        tien_hang += thuoc.don_gia * luong
        for ton, lay in phan_bo_fefo(chi_nhanh, thuoc, luong):
            PhanBoDonHang.objects.create(chi_tiet_don_hang=dong, ton_kho=ton, so_luong=lay)
    don.tien_hang = tien_hang
    don.tong_thanh_toan = tien_hang - don.giam_gia_thanh_vien + don.phi_giao_hang
    don.save(update_fields=["tien_hang", "tong_thanh_toan"])
    if trang_thai == "cho_thanh_toan":
        tao_cho(don, phuong_thuc_thanh_toan)
    ghi_lich_su(don, None, trang_thai, nguoi)
    bao_don_moi(don)
    return don


def dat_giu(nguoi, chi_nhanh, cac_dong):
    """Đặt giữ nhận tại quầy theo đề cương (bản đồ WebGIS và giỏ hàng dùng chung)."""
    return dat_hang(nguoi, chi_nhanh, cac_dong)
