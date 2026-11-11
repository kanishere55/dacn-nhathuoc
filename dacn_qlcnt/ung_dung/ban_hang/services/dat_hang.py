"""Khách đặt đơn: giữ hàng theo FEFO, chụp giá, ghi lịch sử và gửi email xác nhận."""

import math
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_vai_tro
from ung_dung.danh_muc.models import Thuoc
from ung_dung.danh_muc.selectors import them_gia_va_anh
from ung_dung.kho.selectors import luong_ban_duoc
from ung_dung.kho.services.giao_dich import khoa_kho, phan_bo_fefo
from ung_dung.thanh_toan.services.ghi import tao_cho

from ..models import TRANG_THAI_GIU, ChiTietDonHang, DonHang, PhanBoDonHang
from ..thanh_vien import giam_thanh_vien, hang_cua, phan_bo_giam
from .giao_hang import BAN_KINH_GIAO_MET, han_toi_thieu_giao, tinh_phi_giao
from .thong_bao_don import bao_don_moi
from .trang_thai import ghi_lich_su

GIO_GIU_TAI_QUAY = 24
GIO_CHO_XAC_NHAN = 24
PHUT_CHO_THANH_TOAN = 30
PHUONG_THUC_GIAO = ("cod", "chuyen_khoan", "momo")
# Chống một tài khoản giữ hết hàng của chi nhánh (đặt giữ không cần trả trước):
# tối đa 3 đơn còn giữ hàng cùng lúc; mỗi đơn giữ một thuốc không quá nửa lượng chi nhánh
# còn bán được, trừ khi chỉ giữ từ 20 đơn vị cơ sở trở xuống.
SO_DON_GIU_TOI_DA = 3
LUONG_GIU_LUON_DUOC = 20


def _tien(so):
    return f"{int(so):,} đ".replace(",", ".")


class TongTienDaDoi(ValidationError):
    """Tổng tiền tính lúc tạo đơn khác tổng khách đã xem; đơn không được tạo."""

    def __init__(self, tong_cu, tong_moi):
        self.tong_moi = tong_moi
        super().__init__(
            f"Tổng tiền vừa thay đổi từ {_tien(tong_cu)} thành {_tien(tong_moi)} "
            "(giá, khuyến mãi, ưu đãi hoặc phí giao đã cập nhật). Hãy xem lại rồi bấm đặt hàng."
        )


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


def kiem_gioi_han_giu(nguoi, chi_nhanh, yeu_cau, cac_thuoc):
    """Giới hạn số đơn còn giữ hàng của khách và lượng giữ mỗi thuốc trong một đơn."""
    dang_giu = DonHang.objects.filter(
        khach_hang=nguoi, trang_thai__in=TRANG_THAI_GIU, thoi_diem_het_giu__gt=timezone.now()
    ).count()
    if dang_giu >= SO_DON_GIU_TOI_DA:
        raise ValidationError(
            f"Bạn đang có {dang_giu} đơn chờ nhận hoặc chờ xử lý. Mỗi tài khoản giữ hàng tối đa "
            f"{SO_DON_GIU_TOI_DA} đơn cùng lúc; hãy nhận hoặc hủy bớt đơn cũ rồi đặt tiếp."
        )
    con = luong_ban_duoc([chi_nhanh], list(yeu_cau))
    for ma, luong in yeu_cau.items():
        tran = max(LUONG_GIU_LUON_DUOC, math.ceil(con.get((chi_nhanh.pk, ma), 0) / 2))
        if luong > tran:
            thuoc = cac_thuoc[ma]
            raise ValidationError(
                f"{thuoc.ten_thuoc}: mỗi đơn giữ được tối đa {tran} "
                f"{thuoc.don_vi_tinh.ten_don_vi_tinh.lower()} tại chi nhánh này để khách khác "
                "vẫn mua được. Cần số lượng lớn hơn, hãy liên hệ nhà thuốc."
            )


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
    tong_khach_xac_nhan=None,
):
    """Tạo đơn trong một transaction đã khóa kho chi nhánh.

    `giao` (bắt buộc khi giao hàng): ten_nguoi_nhan, so_dien_thoai, dia_chi, vi_tri,
    khoang_cach_met. Quãng đường được tính trước khi gọi để không giữ khóa kho trong
    lúc chờ dịch vụ bản đồ. `tong_khach_xac_nhan`: tổng tiền khách đã xem trên trang đặt
    hàng; khác tổng tính lại thì ném TongTienDaDoi và không tạo đơn.
    """
    kiem_tra_vai_tro(nguoi, "khach_hang")
    # Cùng khách có thể đặt đồng thời từ nhiều phiên và nhiều chi nhánh.
    nguoi = get_user_model().objects.select_for_update(no_key=True).get(pk=nguoi.pk)
    kiem_tra_vai_tro(nguoi, "khach_hang")
    yeu_cau = gop_dong(cac_dong)
    giao_hang = hinh_thuc_nhan == "giao_hang"
    if giao_hang and phuong_thuc_thanh_toan not in PHUONG_THUC_GIAO:
        raise ValidationError("Phương thức thanh toán không dùng được cho đơn giao hàng.")
    if not giao_hang and phuong_thuc_thanh_toan != "tai_quay":
        raise ValidationError("Đơn nhận tại nhà thuốc thanh toán tại quầy.")
    khoa_kho(chi_nhanh)
    cac_thuoc = them_gia_va_anh(
        Thuoc.objects.filter(pk__in=yeu_cau, dang_hoat_dong=True).select_related("don_vi_tinh")
    ).in_bulk()
    if len(cac_thuoc) != len(yeu_cau):
        raise ValidationError("Có thuốc đã ngừng kinh doanh, hãy bỏ khỏi giỏ.")
    kiem_gioi_han_giu(nguoi, chi_nhanh, yeu_cau, cac_thuoc)
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
    het_giu = bay_gio + han_giu
    # Chỉ giữ trên lô còn hạn tới ngày hết giữ; đơn giao cần lô còn hạn ít nhất 30 ngày.
    con_han_den = han_toi_thieu_giao() if giao_hang else timezone.localdate(het_giu)
    don = DonHang(
        ma_don_hang=tao_ma_don(bay_gio),
        khach_hang=nguoi,
        chi_nhanh=chi_nhanh,
        hinh_thuc_nhan=hinh_thuc_nhan,
        trang_thai=trang_thai,
        phuong_thuc_thanh_toan=phuong_thuc_thanh_toan,
        thoi_diem_tao=bay_gio,
        thoi_diem_het_giu=het_giu,
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

    cac_dong_gia = [
        (cac_thuoc[ma], luong, cac_thuoc[ma].don_gia) for ma, luong in sorted(yeu_cau.items())
    ]
    giam = giam_thanh_vien(hang_cua(nguoi)["phan_tram"], cac_dong_gia)
    tien_hang = 0
    for (thuoc, luong, don_gia), phan_giam in zip(
        cac_dong_gia, phan_bo_giam(giam, cac_dong_gia), strict=True
    ):
        dong = ChiTietDonHang.objects.create(
            don_hang=don,
            thuoc=thuoc,
            so_luong=luong,
            gia_niem_yet=thuoc.gia_ban,
            phan_tram_giam=thuoc.phan_tram_giam,
            don_gia=don_gia,
            giam_gia_phan_bo=phan_giam,
        )
        tien_hang += don_gia * luong
        for ton, lay in phan_bo_fefo(chi_nhanh, thuoc, luong, con_han_den=con_han_den):
            PhanBoDonHang.objects.create(chi_tiet_don_hang=dong, ton_kho=ton, so_luong=lay)
    don.tien_hang = tien_hang
    don.giam_gia_thanh_vien = giam
    don.tong_thanh_toan = tien_hang - giam + don.phi_giao_hang
    if tong_khach_xac_nhan is not None and tong_khach_xac_nhan != don.tong_thanh_toan:
        raise TongTienDaDoi(tong_khach_xac_nhan, don.tong_thanh_toan)
    don.save(update_fields=["tien_hang", "giam_gia_thanh_vien", "tong_thanh_toan"])
    if trang_thai == "cho_thanh_toan":
        tao_cho(don, phuong_thuc_thanh_toan)
    ghi_lich_su(don, None, trang_thai, nguoi)
    bao_don_moi(don)
    return don


def dat_giu(nguoi, chi_nhanh, cac_dong):
    """Đặt giữ nhận tại quầy theo đề cương (bản đồ WebGIS và giỏ hàng dùng chung)."""
    return dat_hang(nguoi, chi_nhanh, cac_dong)
