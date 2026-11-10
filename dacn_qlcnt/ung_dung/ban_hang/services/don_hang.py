"""Xử lý đơn sau khi đặt: hủy, xác nhận, giao, hoàn thành, giao thất bại, quá hạn."""

from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.permissions import (
    kiem_tra_quyen_ghi_chi_nhanh,
    kiem_tra_vai_tro,
)
from ung_dung.kho.services.giao_dich import khoa_kho
from ung_dung.thanh_toan.services.ghi import ghi_ngay, ket_thuc_cho

from ..models import DonHang, LichSuDonHang, PhieuBan
from .hoan_kho import hoan_kho
from .phieu_ban import ban_tai_quay
from .thong_bao_don import bao_doi_trang_thai
from .trang_thai import doi_trang_thai


def _khoa_don(don, nguoi, quyen="don_hang.xu_ly"):
    """Kiểm quyền rồi khóa kho chi nhánh trước, đơn sau, cùng thứ tự với đặt hàng."""
    if nguoi is not None:
        if nguoi.vai_tro == "khach_hang":
            kiem_tra_vai_tro(nguoi, "khach_hang")
            if don.khach_hang_id != nguoi.pk:
                raise PermissionDenied("Đơn không thuộc tài khoản của bạn.")
        else:
            kiem_tra_quyen_ghi_chi_nhanh(nguoi, don.chi_nhanh, quyen)
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


# Đơn đang giao mà khách không bấm "Đã nhận hàng" sẽ tự hoàn tất sau số ngày này.
NGAY_TU_HOAN_THANH = 3


def thoi_diem_bat_dau_giao(don):
    lich_su = (
        LichSuDonHang.objects.filter(don_hang=don, den_trang_thai="dang_giao")
        .order_by("-thoi_diem_tao")
        .first()
    )
    return lich_su.thoi_diem_tao if lich_su else None


def han_tu_hoan_thanh(don):
    bat_dau = thoi_diem_bat_dau_giao(don)
    return bat_dau + timedelta(days=NGAY_TU_HOAN_THANH) if bat_dau else None


@transaction.atomic
def xac_nhan_da_giao(nguoi, don):
    """Khách xác nhận đã nhận hàng (hoặc hệ thống tự hoàn tất khi quá hạn, `nguoi` là None).

    Đơn COD ghi nhận tiền người giao đã thu tại thời điểm này. Hạn trả hàng 7 ngày tính từ đây.
    """
    if nguoi is not None and nguoi.vai_tro != "khach_hang":
        raise PermissionDenied("Chỉ khách nhận hàng mới xác nhận đã nhận được hàng.")
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
            nguoi=None,
            ghi_chu="Người giao thu tiền khi giao",
        )
    ghi_chu = (
        "Khách xác nhận đã nhận hàng"
        if nguoi
        else f"Tự hoàn tất sau {NGAY_TU_HOAN_THANH} ngày giao mà khách chưa xác nhận"
    )
    doi_trang_thai(don, "hoan_thanh", nguoi, ghi_chu, them_cot=them_cot)
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


def tu_hoan_thanh_don_dang_giao():
    """Đơn đang giao quá NGAY_TU_HOAN_THANH ngày mà khách chưa xác nhận thì tự hoàn tất."""
    moc = timezone.now() - timedelta(days=NGAY_TU_HOAN_THANH)
    so_don = 0
    for don in DonHang.objects.filter(trang_thai="dang_giao"):
        bat_dau = thoi_diem_bat_dau_giao(don)
        if bat_dau is None or bat_dau > moc:
            continue
        try:
            xac_nhan_da_giao(None, don)
        except ValidationError:
            continue  # đơn vừa đổi trạng thái ở luồng khác
        so_don += 1
    return so_don


def xu_ly_qua_han():
    """Đổi trạng thái các đơn đã quá hạn giữ; chạy định kỳ bằng lệnh quản lý."""
    so_don = tu_hoan_thanh_don_dang_giao()
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
