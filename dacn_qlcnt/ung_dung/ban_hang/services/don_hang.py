"""Xử lý đơn sau khi đặt: hủy, xác nhận, giao, hoàn thành, giao thất bại, quá hạn."""

from collections import defaultdict
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.permissions import (
    kiem_tra_quyen_ghi_chi_nhanh,
    kiem_tra_vai_tro,
)
from ung_dung.kho.models import ChiTietPhieuXuatHuy, PhieuXuatHuy
from ung_dung.kho.services.giao_dich import khoa_kho, ma_chung_tu
from ung_dung.thanh_toan.models import GiaoDichThanhToan
from ung_dung.thanh_toan.services.doi_soat import cap_nhat_trang_thai_thanh_toan
from ung_dung.thanh_toan.services.ghi import ket_thuc_cho

from ..models import DonHang, LichSuDonHang, PhieuBan
from ..selectors import lay_lo_da_xuat
from .giu_hang import han_lo_can_cho_don, phan_bo_lai_don, phan_bo_lai_moi_chi_nhanh
from .hoan_kho import hoan_kho
from .phieu_ban import ban_tai_quay
from .thong_bao_don import bao_doi_trang_thai
from .trang_thai import doi_trang_thai, kiem_tra_chuyen


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
    return (
        DonHang.objects.select_for_update(of=("self",)).select_related("khach_hang").get(pk=don.pk)
    )


def _sau_huy(don):
    """Đơn hủy, hết hạn hoặc giao thất bại: đóng giao dịch chờ, mọi khoản đã thu chờ hoàn.

    Đối soát theo tổng giao dịch nên cả khoản chuyển thiếu (đơn chưa đủ tiền) cũng vào
    hàng chờ hoàn, không bị kẹt.
    """
    ket_thuc_cho(don, "het_han")
    cap_nhat_trang_thai_thanh_toan(don)


@transaction.atomic
def huy_don(nguoi, don, ly_do=""):
    don = _khoa_don(don, nguoi)
    if don.trang_thai == "dang_giu" and don.thoi_diem_het_giu <= timezone.now():
        doi_trang_thai(don, "het_han", nguoi, "Đơn đã quá hạn giữ khi hủy")
        _sau_huy(don)
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


# Sau mốc này cần kiểm tra với đơn vị giao trước khi chốt trạng thái.
NGAY_CAN_DOI_CHIEU_GIAO = 3


def thoi_diem_bat_dau_giao(don):
    lich_su = (
        LichSuDonHang.objects.filter(don_hang=don, den_trang_thai="dang_giao")
        .order_by("-thoi_diem_tao")
        .first()
    )
    return lich_su.thoi_diem_tao if lich_su else None


def han_doi_chieu_giao(don):
    bat_dau = thoi_diem_bat_dau_giao(don)
    return bat_dau + timedelta(days=NGAY_CAN_DOI_CHIEU_GIAO) if bat_dau else None


@transaction.atomic
def xac_nhan_da_giao(nguoi, don):
    kiem_tra_vai_tro(nguoi, "khach_hang")
    return _ghi_giao_xong(_khoa_don(don, nguoi), nguoi, "Khách xác nhận đã nhận hàng")


@transaction.atomic
def xac_nhan_giao_thanh_cong(nguoi, don, ghi_chu):
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, don.chi_nhanh, "don_hang.xu_ly")
    if don.trang_thai != "dang_giao":
        raise ValidationError("Chỉ đơn đang giao mới đối chiếu giao nhận thành công.")
    if not ghi_chu.strip():
        raise ValidationError("Ghi mã giao nhận hoặc căn cứ xác nhận khách đã nhận hàng.")
    return _ghi_giao_xong(
        _khoa_don(don, nguoi), nguoi, f"Nhà thuốc đối chiếu giao hàng: {ghi_chu.strip()}"
    )


def _ghi_giao_xong(don, nguoi, ghi_chu):
    """Hoàn thành giao hàng; khoản COD chờ đối soát đến khi nhà thuốc thực nhận tiền."""
    doi_trang_thai(don, "hoan_thanh", nguoi, ghi_chu)
    if (
        don.phuong_thuc_thanh_toan == "cod"
        and not GiaoDichThanhToan.objects.filter(don_hang=don, phuong_thuc="cod").exists()
    ):
        GiaoDichThanhToan.objects.create(
            ma_giao_dich_thanh_toan=ma_chung_tu("GD"),
            don_hang=don,
            phieu_ban=PhieuBan.objects.filter(don_hang=don).first(),
            loai_giao_dich="thu",
            phuong_thuc="cod",
            so_tien=don.tong_thanh_toan,
            ghi_chu="Người giao thu tiền khi giao, chờ nộp lại nhà thuốc",
        )
    cap_nhat_trang_thai_thanh_toan(don)
    bao_doi_trang_thai(don)
    return don


def _huy_hang_da_xuat(nguoi, phieu_ban, theo_lo, ly_do):
    phieu = PhieuXuatHuy.objects.create(
        ma_phieu_xuat_huy=ma_chung_tu("PX"),
        chi_nhanh=phieu_ban.chi_nhanh,
        nguoi_lap=nguoi,
        loai_xuat_huy="hu_hong",
        co_tru_ton=False,
        ghi_chu=f"Hủy hàng giao thất bại theo phiếu bán {phieu_ban.ma_phieu_ban}. {ly_do}",
    )
    ChiTietPhieuXuatHuy.objects.bulk_create(
        ChiTietPhieuXuatHuy(phieu_xuat_huy=phieu, lo_thuoc_id=ma, so_luong=luong)
        for ma, luong in theo_lo.items()
    )
    return phieu


@transaction.atomic
def bao_giao_that_bai(nguoi, don, ly_do, *, xu_ly_hang="", so_luong_theo_lo=None):
    """Ghi giao thất bại sau khi đối chiếu tình trạng hàng với đơn vị giao."""
    if not ly_do:
        raise ValidationError("Hãy ghi lý do giao không thành công.")
    if xu_ly_hang not in ("hoan_kho", "da_huy", "that_lac", "theo_lo"):
        raise ValidationError("Chọn kết quả xử lý hàng sau khi đối chiếu với người giao.")
    don = _khoa_don(don, nguoi)
    kiem_tra_chuyen(don, "giao_that_bai", nguoi)
    phieu_ban = PhieuBan.objects.get(don_hang=don)
    cac_lo = list(lay_lo_da_xuat(don))
    if not cac_lo:
        raise ValidationError("Không tìm thấy các lô đã xuất của đơn. Kiểm tra lại phiếu bán.")
    if xu_ly_hang == "theo_lo":
        if set(so_luong_theo_lo or {}) != {dong.pk for dong in cac_lo}:
            raise ValidationError("Hãy ghi kết quả cho từng lô đã xuất.")
    else:
        so_luong_theo_lo = {
            dong.pk: tuple(
                dong.so_luong if ma == xu_ly_hang else 0
                for ma in ("hoan_kho", "da_huy", "that_lac")
            )
            for dong in cac_lo
        }
    hoan, huy, that_lac = {}, defaultdict(int), []
    for dong in cac_lo:
        nhap, da_huy, mat = so_luong_theo_lo[dong.pk]
        lo = dong.ton_kho.lo_thuoc
        if min(nhap, da_huy, mat) < 0 or nhap + da_huy + mat != dong.so_luong:
            raise ValidationError(f"Lô {lo.ma_lo_thuoc}: tổng phải bằng {dong.so_luong} đã xuất.")
        if nhap:
            hoan[dong.pk] = nhap
        if da_huy:
            huy[lo.pk] += da_huy
        if mat:
            that_lac.append(
                f"{dong.chi_tiet_phieu_ban.ten_thuoc_luc_ban}, lô {lo.ma_lo_thuoc}: {mat}"
            )
    ghi_chu = [ly_do]
    if huy:
        kiem_tra_quyen_ghi_chi_nhanh(nguoi, don.chi_nhanh, "xuat_huy.tao")
        phieu = _huy_hang_da_xuat(nguoi, phieu_ban, huy, ly_do)
        ghi_chu.append(f"Hủy theo phiếu {phieu.ma_phieu_xuat_huy}.")
    if hoan:
        phieu = hoan_kho(nguoi, phieu_ban, "giao_that_bai", luong_theo_phan_bo=hoan)
        ghi_chu.append(f"Hoàn kho theo phiếu {phieu.ma_phieu_hoan_kho}.")
    if that_lac:
        ghi_chu.append(f"Thất lạc ({'; '.join(that_lac)}).")
    doi_trang_thai(don, "giao_that_bai", nguoi, " ".join(ghi_chu))
    _sau_huy(don)
    bao_doi_trang_thai(don, ly_do)
    return don


def chuyen_da_thanh_toan(don, nguoi, ghi_chu):
    """Đơn chờ thanh toán (đã khóa) nhận đủ tiền: sang chờ xác nhận, gia hạn giữ 24 giờ.

    Gia hạn xong thì kiểm lại lô đang giữ: lô không còn hạn tới hạn giữ mới (hoặc đã khóa)
    được dời sang lô khác. Không đủ lô thay thế thì giữ nguyên phân bổ cũ và ghi lưu ý vào
    lịch sử để nhân viên liên hệ khách, vì tiền đã nhận nên không hủy đơn tự động.
    """
    from .dat_hang import GIO_CHO_XAC_NHAN

    if don.trang_thai != "cho_thanh_toan":
        return don
    het_giu_moi = timezone.now() + timedelta(hours=GIO_CHO_XAC_NHAN)
    try:
        with transaction.atomic():
            phan_bo_lai_don(don, con_han_den=han_lo_can_cho_don(don, het_giu_moi))
    except ValidationError as loi:
        ghi_chu = f"{ghi_chu}. Cần kiểm tra: {' '.join(loi.messages)}"
    don.trang_thai_thanh_toan = "da_thanh_toan"
    don.thoi_diem_het_giu = het_giu_moi
    doi_trang_thai(
        don,
        "cho_xac_nhan",
        nguoi,
        ghi_chu,
        them_cot=("trang_thai_thanh_toan", "thoi_diem_het_giu"),
    )
    bao_doi_trang_thai(don)
    return don


@transaction.atomic
def xac_nhan_da_thanh_toan(don, nguoi=None, ghi_chu="Đã nhận thanh toán trực tuyến"):
    """Khóa đơn rồi chuyển chờ xác nhận như chuyen_da_thanh_toan."""
    return chuyen_da_thanh_toan(_khoa_don(don, nguoi), nguoi, ghi_chu)


QUA_HAN = {
    "dang_giu": ("het_han", "Quá 24 giờ chưa nhận tại quầy"),
    "cho_thanh_toan": ("da_huy", "Quá hạn thanh toán trực tuyến"),
    "cho_xac_nhan": ("da_huy", "Nhà thuốc chưa xác nhận trong 24 giờ"),
}


def xu_ly_qua_han():
    """Đổi trạng thái các đơn đã quá hạn giữ; chạy định kỳ bằng lệnh quản lý.

    Kèm theo: dời phần giữ của đơn còn hiệu lực khỏi lô vừa hết hạn hoặc bị khóa bán.
    """
    phan_bo_lai_moi_chi_nhanh()
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
