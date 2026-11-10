"""Nhận kết quả thanh toán từ SePay, MoMo hoặc nhân viên và hoàn tiền."""

import re
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from ung_dung.ban_hang.models import DonHang
from ung_dung.ban_hang.services.don_hang import _khoa_don, xac_nhan_da_thanh_toan
from ung_dung.ban_hang.services.thong_bao_don import bao_doi_trang_thai
from ung_dung.ban_hang.services.trang_thai import doi_trang_thai
from ung_dung.chung.permissions import (
    kiem_tra_quyen_ghi_chi_nhanh,
)

from ..models import PHUONG_THUC, GiaoDichThanhToan
from .ghi import ghi_ngay, ket_thuc_cho

# Mã đơn hiện tại (DH + yymmdd + 5 ký tự) và mã dài của các đơn tạo trước đó.
CAC_MAU_MA_DON = (
    re.compile(r"DH\d{6}[2-9A-HJKMNP-Z]{5}", re.IGNORECASE),
    re.compile(r"DH[0-9A-F]{20}", re.IGNORECASE),
)


def tim_don_trong_noi_dung(noi_dung):
    cac_ma = {ma.upper() for mau in CAC_MAU_MA_DON for ma in mau.findall(noi_dung)}
    return DonHang.objects.filter(ma_don_hang__in=cac_ma).first() if cac_ma else None


def nhan_tien(don, *, phuong_thuc, so_tien, ma_tham_chieu=None, nguoi=None, ghi_chu=""):
    """Ghi tiền khách đã trả cho đơn trả trước. Trả False nếu mã tham chiếu đã ghi.

    Đủ tiền trong hạn giữ thì đơn sang chờ xác nhận. Thiếu tiền giữ nguyên đơn để
    nhân viên liên hệ. Tiền tới khi đơn đã hủy hoặc quá hạn (kho có thể đã bán cho
    người khác) được ghi nhận rồi chuyển chờ hoàn tiền.
    """
    so_tien = Decimal(so_tien)
    with transaction.atomic():
        don = _khoa_don(don, None)
        if (
            ma_tham_chieu
            and GiaoDichThanhToan.objects.filter(
                phuong_thuc=phuong_thuc, ma_tham_chieu=ma_tham_chieu
            ).exists()
        ):
            return False
        if don.trang_thai == "cho_thanh_toan" and don.thoi_diem_het_giu <= timezone.now():
            doi_trang_thai(don, "da_huy", None, "Quá hạn thanh toán trực tuyến")
            ket_thuc_cho(don, "het_han")
            bao_doi_trang_thai(don, "Tiền đến sau khi hết hạn giữ hàng, nhà thuốc sẽ hoàn lại.")
        cho = (
            GiaoDichThanhToan.objects.select_for_update()
            .filter(don_hang=don, trang_thai="cho", phuong_thuc=phuong_thuc)
            .first()
        )
        du_tien = so_tien >= don.tong_thanh_toan
        if cho and so_tien == cho.so_tien:
            cho.trang_thai = "thanh_cong"
            cho.ma_tham_chieu = ma_tham_chieu or None
            cho.ghi_chu = ghi_chu
            cho.nguoi_xac_nhan = nguoi
            cho.thoi_diem_hoan_tat = timezone.now()
            cho.save()
        else:
            ghi_ngay(
                loai="thu",
                phuong_thuc=phuong_thuc,
                so_tien=so_tien,
                don_hang=don,
                nguoi=nguoi,
                ma_tham_chieu=ma_tham_chieu,
                ghi_chu=ghi_chu if du_tien else f"Chuyển thiếu tiền. {ghi_chu}".strip(),
            )
        if don.trang_thai in ("da_huy", "het_han"):
            if don.trang_thai_thanh_toan in ("chua_thanh_toan", "da_hoan_tien"):
                don.trang_thai_thanh_toan = "cho_hoan_tien"
                don.save(update_fields=["trang_thai_thanh_toan"])
        elif du_tien and don.trang_thai == "cho_thanh_toan":
            ten = dict(PHUONG_THUC).get(phuong_thuc, phuong_thuc).lower()
            xac_nhan_da_thanh_toan(
                don, nguoi, f"Đã nhận {so_tien:,.0f} đ qua {ten}".replace(",", ".")
            )
    return True


def xu_ly_sepay(du_lieu):
    """Webhook SePay: chỉ xử lý tiền vào có mã đơn trong nội dung."""
    if du_lieu.get("transferType") != "in":
        return "bo_qua"
    noi_dung = f"{du_lieu.get('code') or ''} {du_lieu.get('content') or ''}"
    don = tim_don_trong_noi_dung(noi_dung)
    if don is None:
        return "khong_khop"
    so_tien = Decimal(str(du_lieu.get("transferAmount") or 0))
    if so_tien <= 0:
        return "bo_qua"
    da_ghi = nhan_tien(
        don,
        phuong_thuc="chuyen_khoan",
        so_tien=so_tien,
        ma_tham_chieu=f"sepay-{du_lieu.get('id')}",
        ghi_chu=" ".join(str(du_lieu.get("content") or "").split())[:200],
    )
    return "da_ghi" if da_ghi else "trung"


def xu_ly_ket_qua_momo(du_lieu):
    """Kết quả MoMo (IPN hoặc trang quay về) đã kiểm chữ ký."""
    giao_dich = (
        GiaoDichThanhToan.objects.select_related("don_hang")
        .filter(ma_giao_dich_thanh_toan=du_lieu.get("orderId"), phuong_thuc="momo")
        .first()
    )
    if giao_dich is None or giao_dich.don_hang is None:
        return "khong_khop"
    if str(du_lieu.get("resultCode")) != "0":
        GiaoDichThanhToan.objects.filter(pk=giao_dich.pk, trang_thai="cho").update(
            trang_thai="that_bai",
            ghi_chu=" ".join(str(du_lieu.get("message", "")).split())[:200],
            thoi_diem_hoan_tat=timezone.now(),
        )
        return "that_bai"
    if giao_dich.trang_thai == "thanh_cong":
        return "trung"
    da_ghi = nhan_tien(
        giao_dich.don_hang,
        phuong_thuc="momo",
        so_tien=du_lieu.get("amount", 0),
        ma_tham_chieu=f"momo-{du_lieu.get('transId')}",
        ghi_chu="Thanh toán qua ví MoMo",
    )
    return "da_ghi" if da_ghi else "trung"


def xac_nhan_tay(nguoi, don, ma_tham_chieu=""):
    """Nhân viên đối chiếu sao kê và xác nhận khách đã chuyển khoản đủ."""
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, don.chi_nhanh, "don_hang.xu_ly")
    if don.trang_thai != "cho_thanh_toan":
        raise ValidationError("Đơn không ở trạng thái chờ thanh toán.")
    nhan_tien(
        don,
        phuong_thuc=don.phuong_thuc_thanh_toan,
        so_tien=don.tong_thanh_toan,
        ma_tham_chieu=f"tay-{ma_tham_chieu}" if ma_tham_chieu else None,
        nguoi=nguoi,
        ghi_chu="Nhân viên xác nhận đã nhận chuyển khoản",
    )


def so_tien_da_thu(don):
    tong = lambda loai: (  # noqa: E731
        GiaoDichThanhToan.objects.filter(
            don_hang=don, loai_giao_dich=loai, trang_thai="thanh_cong"
        ).aggregate(tong=Sum("so_tien"))["tong"]
        or Decimal(0)
    )
    return tong("thu") - tong("hoan")


@transaction.atomic
def hoan_tien(nguoi, don, *, phuong_thuc, ma_tham_chieu="", ghi_chu=""):
    """Quản lý chi nhánh ghi nhận đã trả lại tiền cho khách (chuyển khoản, tiền mặt, MoMo)."""
    if nguoi is None:
        raise PermissionDenied("Hoàn tiền cần người xác nhận.")
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, don.chi_nhanh, "don_hang.hoan_tien")
    don = _khoa_don(don, nguoi, "don_hang.hoan_tien")
    if don.trang_thai_thanh_toan != "cho_hoan_tien":
        raise ValidationError("Đơn không có khoản chờ hoàn tiền.")
    so_tien = so_tien_da_thu(don)
    if so_tien <= 0:
        raise ValidationError("Đơn chưa ghi nhận khoản thu nào để hoàn.")
    ghi_ngay(
        loai="hoan",
        phuong_thuc=phuong_thuc,
        so_tien=so_tien,
        don_hang=don,
        nguoi=nguoi,
        ma_tham_chieu=f"hoan-{ma_tham_chieu}" if ma_tham_chieu else None,
        ghi_chu=ghi_chu or "Hoàn tiền cho khách",
    )
    don.trang_thai_thanh_toan = "da_hoan_tien"
    don.save(update_fields=["trang_thai_thanh_toan"])
    bao_doi_trang_thai(don, f"Đã hoàn {so_tien:,.0f} đ".replace(",", "."))
    return don
