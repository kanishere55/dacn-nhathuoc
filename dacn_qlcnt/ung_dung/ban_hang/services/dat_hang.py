"""Khách đặt giữ: giữ hàng theo FEFO, chụp giá, ghi lịch sử và gửi email xác nhận."""

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

from ..models import TRANG_THAI_GIU, ChiTietDonHang, DonHang, PhanBoDonHang
from ..thanh_vien import giam_thanh_vien, hang_cua, phan_bo_giam
from .thong_bao_don import bao_don_moi
from .trang_thai import ghi_lich_su

GIO_GIU_TAI_QUAY = 24
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
            "(giá, khuyến mãi hoặc ưu đãi đã cập nhật). Hãy xem lại rồi bấm đặt giữ."
        )


# Bỏ 0, 1, I, L, O để khách đọc mã tại quầy không nhầm.
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
            f"Bạn đang có {dang_giu} đơn đang giữ hàng. Mỗi tài khoản giữ hàng tối đa "
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
def dat_hang(nguoi, chi_nhanh, cac_dong, *, ghi_chu_khach="", tong_khach_xac_nhan=None):
    """Tạo đơn đặt giữ trong một transaction đã khóa kho chi nhánh.

    Đơn được xác nhận ngay khi chi nhánh đủ toàn bộ số lượng (Q03): mỗi dòng giữ trên các lô
    còn hạn tới hết hạn giữ theo FEFO. Khách nhận và trả tiền tại quầy trong 24 giờ.
    `tong_khach_xac_nhan`: tổng tiền khách đã xem trên trang đặt giữ; khác tổng tính lại thì
    ném TongTienDaDoi và không tạo đơn.
    """
    kiem_tra_vai_tro(nguoi, "khach_hang")
    # Cùng khách có thể đặt đồng thời từ nhiều phiên và nhiều chi nhánh.
    nguoi = get_user_model().objects.select_for_update(no_key=True).get(pk=nguoi.pk)
    kiem_tra_vai_tro(nguoi, "khach_hang")
    yeu_cau = gop_dong(cac_dong)
    khoa_kho(chi_nhanh)
    cac_thuoc = them_gia_va_anh(
        Thuoc.objects.filter(pk__in=yeu_cau, dang_hoat_dong=True).select_related("don_vi_tinh")
    ).in_bulk()
    if len(cac_thuoc) != len(yeu_cau):
        raise ValidationError("Có thuốc đã ngừng kinh doanh, hãy bỏ khỏi giỏ.")
    kiem_gioi_han_giu(nguoi, chi_nhanh, yeu_cau, cac_thuoc)

    bay_gio = timezone.now()
    het_giu = bay_gio + timedelta(hours=GIO_GIU_TAI_QUAY)
    # Chỉ giữ trên lô còn hạn tới ngày hết giữ.
    con_han_den = timezone.localdate(het_giu)
    don = DonHang.objects.create(
        ma_don_hang=tao_ma_don(bay_gio),
        khach_hang=nguoi,
        chi_nhanh=chi_nhanh,
        trang_thai="dang_giu",
        thoi_diem_tao=bay_gio,
        thoi_diem_het_giu=het_giu,
        ghi_chu_khach=ghi_chu_khach,
    )

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
    don.tong_thanh_toan = tien_hang - giam
    if tong_khach_xac_nhan is not None and tong_khach_xac_nhan != don.tong_thanh_toan:
        raise TongTienDaDoi(tong_khach_xac_nhan, don.tong_thanh_toan)
    don.save(update_fields=["tien_hang", "giam_gia_thanh_vien", "tong_thanh_toan"])
    ghi_lich_su(don, None, "dang_giu", nguoi)
    bao_don_moi(don)
    return don


def dat_giu(nguoi, chi_nhanh, cac_dong):
    """Đặt giữ từ bản đồ WebGIS (dùng chung nghiệp vụ với trang đặt giữ từ giỏ)."""
    return dat_hang(nguoi, chi_nhanh, cac_dong)
