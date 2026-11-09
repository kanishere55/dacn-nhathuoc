"""Trả hàng: khách gửi yêu cầu cho đơn đã hoàn thành, quản lý chi nhánh duyệt và hoàn tiền.

Thuốc đã bán chỉ nhận trả khi lỗi thuộc nhà thuốc (giao sai, hư hỏng, hết hạn). Hàng
trả không quay lại tồn bán được; quản lý lập phiếu xuất hủy cho lượng đã nhận về.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_quyen_ghi_chi_nhanh, kiem_tra_vai_tro
from ung_dung.thanh_toan.services.cong import so_tien_da_thu
from ung_dung.thanh_toan.services.ghi import ghi_ngay

from ..models import (
    AnhTraHang,
    ChiTietTraHang,
    DonHang,
    LichSuDonHang,
    YeuCauTraHang,
)
from .dat_hang import KY_TU_MA_DON
from .thong_bao_don import bao_tra_hang

NGAY_DUOC_TRA = 7
SO_ANH_TOI_DA = 4
TRANG_THAI_MO = ("cho_duyet", "da_duyet")


def thoi_diem_hoan_thanh(don):
    lich_su = (
        LichSuDonHang.objects.filter(don_hang=don, den_trang_thai="hoan_thanh")
        .order_by("-thoi_diem_tao")
        .first()
    )
    return lich_su.thoi_diem_tao if lich_su else None


def han_tra_hang(don):
    xong = thoi_diem_hoan_thanh(don)
    return xong + timedelta(days=NGAY_DUOC_TRA) if xong else None


def ly_do_khong_tra_duoc(don):
    """Chuỗi giải thích vì sao đơn chưa gửi yêu cầu được; None nếu được gửi."""
    if don.trang_thai != "hoan_thanh":
        return "Chỉ gửi yêu cầu trả hàng cho đơn đã hoàn thành."
    han = han_tra_hang(don)
    if han is None or han < timezone.now():
        return f"Đã quá {NGAY_DUOC_TRA} ngày kể từ khi nhận hàng."
    if don.cac_yeu_cau_tra_hang.filter(trang_thai__in=TRANG_THAI_MO).exists():
        return "Đơn đang có yêu cầu trả hàng chưa xử lý xong."
    if not any(con > 0 for con in so_luong_con_tra(don).values()):
        return "Các thuốc trong đơn đã được trả hết."
    return None


def so_luong_con_tra(don):
    """{id dòng đơn: số lượng còn trả được} trừ các yêu cầu không bị từ chối."""
    da_tra = dict(
        ChiTietTraHang.objects.filter(yeu_cau_tra_hang__don_hang=don)
        .exclude(yeu_cau_tra_hang__trang_thai="tu_choi")
        .values("chi_tiet_don_hang")
        .annotate(tong=Sum("so_luong"))
        .values_list("chi_tiet_don_hang", "tong")
    )
    return {dong.pk: dong.so_luong - da_tra.get(dong.pk, 0) for dong in don.cac_dong.all()}


def _tao_ma(thoi_diem):
    import secrets

    ngay = timezone.localtime(thoi_diem).strftime("%y%m%d")
    for _ in range(8):
        ma = "TH" + ngay + "".join(secrets.choice(KY_TU_MA_DON) for _ in range(5))
        if not YeuCauTraHang.objects.filter(ma_yeu_cau_tra_hang=ma).exists():
            return ma
    raise ValidationError("Chưa cấp được mã yêu cầu, vui lòng thử lại.")


@transaction.atomic
def tao_yeu_cau(nguoi, don, *, ly_do, mo_ta, cac_dong, cac_anh):
    """`cac_dong`: {id dòng đơn: số lượng trả}; `cac_anh`: tệp ảnh minh chứng."""
    kiem_tra_vai_tro(nguoi, "khach_hang")
    don = DonHang.objects.select_for_update().get(pk=don.pk)
    if don.khach_hang_id != nguoi.pk:
        raise PermissionDenied("Đơn không thuộc tài khoản của bạn.")
    ly_do_chan = ly_do_khong_tra_duoc(don)
    if ly_do_chan:
        raise ValidationError(ly_do_chan)
    con_lai = so_luong_con_tra(don)
    cac_dong = {int(ma): int(luong) for ma, luong in cac_dong.items() if int(luong) > 0}
    if not cac_dong:
        raise ValidationError("Chọn ít nhất một thuốc và số lượng cần trả.")
    for ma, luong in cac_dong.items():
        if ma not in con_lai or luong > con_lai[ma]:
            raise ValidationError("Số lượng trả vượt số lượng đã mua.")
    if not cac_anh:
        raise ValidationError("Cần ít nhất một ảnh chụp tình trạng thuốc.")
    if len(cac_anh) > SO_ANH_TOI_DA:
        raise ValidationError(f"Tối đa {SO_ANH_TOI_DA} ảnh.")
    dong_don = {dong.pk: dong for dong in don.cac_dong.all()}
    tien_hang = sum((dong_don[ma].don_gia * luong for ma, luong in cac_dong.items()), Decimal(0))
    da_hoan = sum(
        (yc.so_tien_hoan for yc in don.cac_yeu_cau_tra_hang.filter(trang_thai="da_hoan_tien")),
        Decimal(0),
    )
    so_tien = min(tien_hang, max(so_tien_da_thu(don) - da_hoan, Decimal(0)))
    bay_gio = timezone.now()
    yeu_cau = YeuCauTraHang.objects.create(
        ma_yeu_cau_tra_hang=_tao_ma(bay_gio),
        don_hang=don,
        ly_do=ly_do,
        mo_ta=mo_ta.strip(),
        so_tien_hoan=so_tien,
    )
    ChiTietTraHang.objects.bulk_create(
        ChiTietTraHang(yeu_cau_tra_hang=yeu_cau, chi_tiet_don_hang_id=ma, so_luong=luong)
        for ma, luong in sorted(cac_dong.items())
    )
    for thu_tu, tep in enumerate(cac_anh):
        anh = AnhTraHang(yeu_cau_tra_hang=yeu_cau, thu_tu=thu_tu)
        anh.gan_du_lieu(tep)
        anh.save()
    bao_tra_hang(yeu_cau)
    return yeu_cau


def _khoa_yeu_cau(nguoi, yeu_cau, trang_thai):
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, yeu_cau.don_hang.chi_nhanh, quan_ly=True)
    yeu_cau = (
        YeuCauTraHang.objects.select_for_update().select_related("don_hang").get(pk=yeu_cau.pk)
    )
    if yeu_cau.trang_thai != trang_thai:
        raise ValidationError("Yêu cầu đã được xử lý ở bước khác, hãy tải lại trang.")
    return yeu_cau


@transaction.atomic
def duyet(nguoi, yeu_cau, ghi_chu=""):
    """Quản lý đã nhận và kiểm hàng trả về; số tiền hoàn giữ theo giá đã mua."""
    yeu_cau = _khoa_yeu_cau(nguoi, yeu_cau, "cho_duyet")
    yeu_cau.trang_thai = "da_duyet"
    yeu_cau.ghi_chu_xu_ly = ghi_chu.strip()
    yeu_cau.nguoi_xu_ly = nguoi
    yeu_cau.thoi_diem_xu_ly = timezone.now()
    yeu_cau.save()
    bao_tra_hang(yeu_cau)
    return yeu_cau


@transaction.atomic
def tu_choi(nguoi, yeu_cau, ly_do):
    if not ly_do.strip():
        raise ValidationError("Cần ghi lý do từ chối để khách nắm được.")
    yeu_cau = _khoa_yeu_cau(nguoi, yeu_cau, "cho_duyet")
    yeu_cau.trang_thai = "tu_choi"
    yeu_cau.ghi_chu_xu_ly = ly_do.strip()
    yeu_cau.nguoi_xu_ly = nguoi
    yeu_cau.thoi_diem_xu_ly = timezone.now()
    yeu_cau.save()
    bao_tra_hang(yeu_cau)
    return yeu_cau


@transaction.atomic
def hoan_tien_tra_hang(nguoi, yeu_cau, *, phuong_thuc, ma_tham_chieu=""):
    yeu_cau = _khoa_yeu_cau(nguoi, yeu_cau, "da_duyet")
    don = DonHang.objects.select_for_update().get(pk=yeu_cau.don_hang_id)
    if yeu_cau.so_tien_hoan > 0:
        ghi_ngay(
            loai="hoan",
            phuong_thuc=phuong_thuc,
            so_tien=yeu_cau.so_tien_hoan,
            don_hang=don,
            nguoi=nguoi,
            ma_tham_chieu=f"tra-{ma_tham_chieu}" if ma_tham_chieu else None,
            ghi_chu=f"Hoàn tiền trả hàng {yeu_cau.ma_yeu_cau_tra_hang}",
        )
    yeu_cau.trang_thai = "da_hoan_tien"
    yeu_cau.save(update_fields=["trang_thai"])
    if so_tien_da_thu(don) <= 0:
        don.trang_thai_thanh_toan = "da_hoan_tien"
        don.save(update_fields=["trang_thai_thanh_toan"])
    bao_tra_hang(yeu_cau)
    return yeu_cau
