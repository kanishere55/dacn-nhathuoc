"""Xử lý đơn sau khi đặt: hủy, xác nhận, giao, hoàn thành, giao thất bại, quá hạn."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.permissions import (
    NHAN_SU_CHI_NHANH,
    kiem_tra_quyen_ghi_chi_nhanh,
    kiem_tra_vai_tro,
)
from ung_dung.kho.services.giao_dich import khoa_kho
from ung_dung.thanh_toan.services.ghi import ghi_ngay, ket_thuc_cho

from ..models import DonHang, PhieuBan
from .hoan_kho import hoan_kho
from .phieu_ban import ban_tai_quay
from .thong_bao_don import bao_doi_trang_thai
from .trang_thai import doi_trang_thai


def _khoa_don(don, nguoi):
    """Kiểm quyền rồi khóa kho chi nhánh trước, đơn sau, cùng thứ tự với đặt hàng."""
    if nguoi is not None:
        kiem_tra_vai_tro(nguoi, "khach_hang", *NHAN_SU_CHI_NHANH)
        if nguoi.vai_tro == "khach_hang":
            if don.khach_hang_id != nguoi.pk:
                raise PermissionDenied("Đơn không thuộc tài khoản của bạn.")
        else:
            kiem_tra_quyen_ghi_chi_nhanh(nguoi, don.chi_nhanh)
    khoa_kho(don.chi_nhanh, cho_phep_ngung=True)
    return DonHang.objects.select_for_update().select_related("khach_hang").get(pk=don.pk)


def _sau_huy(don):
    """Đơn đã thu tiền trực tuyến mà bị hủy thì chuyển sang chờ hoàn tiền."""
    ket_thuc_cho(don, "het_han")
    if don.trang_thai_thanh_toan == "da_thanh_toan":
        don.trang_thai_thanh_toan = "cho_hoan_tien"
        don.save(update_fields=["trang_thai_thanh_toan"])


@transaction.atomic
def huy_don(nguoi, don, ly_do=""):
    don = _khoa_don(don, nguoi)
    if don.trang_thai == "dang_giu" and don.thoi_diem_het_giu <= timezone.now():
        doi_trang_thai(don, "het_han", nguoi, "Đơn đã quá hạn giữ khi hủy")
    else:
        if don.trang_thai == "dang_chuan_bi":
            hoan_kho(nguoi, PhieuBan.objects.get(don_hang=don), "huy_don")
        ghi_chu = ly_do or (
            "Khách hủy đơn" if nguoi.vai_tro == "khach_hang" else "Nhà thuốc hủy đơn"
        )
        doi_trang_thai(don, "da_huy", nguoi, ghi_chu)
        _sau_huy(don)
    bao_doi_trang_thai(don, ly_do)
    return don


def xac_nhan_don(nguoi, don):
    """Nhân viên nhận đơn giao hàng: lập phiếu bán, xuất kho, chuyển đang chuẩn bị."""
    return ban_tai_quay(nguoi, don.chi_nhanh, [], don_hang=don)


@transaction.atomic
def giao_cho_van_chuyen(nguoi, don):
    don = _khoa_don(don, nguoi)
    doi_trang_thai(don, "dang_giao", nguoi, "Đã giao cho người vận chuyển")
    bao_doi_trang_thai(don)
    return don


@transaction.atomic
def xac_nhan_da_giao(nguoi, don):
    don = _khoa_don(don, nguoi)
    them_cot = ()
    if don.phuong_thuc_thanh_toan == "cod":
        don.trang_thai_thanh_toan = "da_thanh_toan"
        them_cot = ("trang_thai_thanh_toan",)
        ghi_ngay(
            loai="thu",
            phuong_thuc="cod",
            so_tien=don.tong_thanh_toan,
            don_hang=don,
            phieu_ban=PhieuBan.objects.filter(don_hang=don).first(),
            nguoi=nguoi,
            ghi_chu="Người giao thu tiền khi giao",
        )
    doi_trang_thai(don, "hoan_thanh", nguoi, "Khách đã nhận hàng", them_cot=them_cot)
    bao_doi_trang_thai(don)
    return don


@transaction.atomic
def bao_giao_that_bai(nguoi, don, ly_do):
    if not ly_do:
        raise ValidationError("Hãy ghi lý do giao không thành công.")
    don = _khoa_don(don, nguoi)
    doi_trang_thai(don, "giao_that_bai", nguoi, ly_do)
    hoan_kho(nguoi, PhieuBan.objects.get(don_hang=don), "giao_that_bai")
    _sau_huy(don)
    bao_doi_trang_thai(don, ly_do)
    return don


@transaction.atomic
def xac_nhan_da_thanh_toan(don, nguoi=None, ghi_chu="Đã nhận thanh toán trực tuyến"):
    """Đơn chờ thanh toán đã nhận đủ tiền: chuyển chờ xác nhận và gia hạn giữ 24 giờ."""
    from datetime import timedelta

    from .dat_hang import GIO_CHO_XAC_NHAN

    don = _khoa_don(don, nguoi)
    if don.trang_thai != "cho_thanh_toan":
        return don
    don.trang_thai_thanh_toan = "da_thanh_toan"
    don.thoi_diem_het_giu = timezone.now() + timedelta(hours=GIO_CHO_XAC_NHAN)
    doi_trang_thai(
        don,
        "cho_xac_nhan",
        nguoi,
        ghi_chu,
        them_cot=("trang_thai_thanh_toan", "thoi_diem_het_giu"),
    )
    bao_doi_trang_thai(don)
    return don


QUA_HAN = {
    "dang_giu": ("het_han", "Quá 24 giờ chưa nhận tại quầy"),
    "cho_thanh_toan": ("da_huy", "Quá hạn thanh toán trực tuyến"),
    "cho_xac_nhan": ("da_huy", "Nhà thuốc chưa xác nhận trong 24 giờ"),
}


def xu_ly_qua_han():
    """Đổi trạng thái các đơn đã quá hạn giữ; chạy định kỳ bằng lệnh quản lý."""
    so_don = 0
    for ma in DonHang.objects.filter(
        trang_thai__in=QUA_HAN, thoi_diem_het_giu__lte=timezone.now()
    ).values_list("pk", flat=True):
        with transaction.atomic():
            don = _khoa_don(DonHang.objects.select_related("chi_nhanh").get(pk=ma), None)
            if don.trang_thai not in QUA_HAN or don.thoi_diem_het_giu > timezone.now():
                continue
            den, ghi_chu = QUA_HAN[don.trang_thai]
            doi_trang_thai(don, den, None, ghi_chu)
            _sau_huy(don)
            bao_doi_trang_thai(don, ghi_chu)
            so_don += 1
    return so_don
