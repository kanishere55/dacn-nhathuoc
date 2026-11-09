import re
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.danh_muc.models import Thuoc
from ung_dung.danh_muc.selectors import them_gia_va_anh
from ung_dung.kho.services.giao_dich import (
    doi_ve_co_so,
    khoa_chi_nhanh,
    ma_chung_tu,
    phan_bo_fefo,
    thay_doi_ton,
)
from ung_dung.thanh_toan.services.ghi import ghi_ngay

from ..models import MA_DON_THUOC, ChiTietPhieuBan, DonHang, PhanBoPhieuBan, PhieuBan
from ..selectors import tong_tien_ban
from .thong_bao_don import bao_doi_trang_thai
from .trang_thai import doi_trang_thai, kiem_tra_chuyen

THONG_BAO_KE_DON = (
    "Phiếu có thuốc kê đơn: dược sĩ phải kiểm tra đơn thuốc, ghi họ tên bác sĩ kê đơn "
    "và cơ sở khám bệnh."
)
PHUONG_THUC_TAI_QUAY = ("tien_mat", "chuyen_khoan")


def _thong_tin_don_thuoc(co_ke_don, don_thuoc):
    """Chuẩn hóa thông tin đơn thuốc; phiếu không có thuốc kê đơn thì bỏ trống."""
    if not co_ke_don:
        return {
            "da_kiem_tra_don_thuoc": False,
            "ma_don_thuoc": None,
            "ten_nguoi_ke_don": "",
            "noi_kham_benh": "",
        }
    don_thuoc = don_thuoc or {}
    thong_tin = {
        "da_kiem_tra_don_thuoc": bool(don_thuoc.get("da_kiem_tra_don_thuoc")),
        "ma_don_thuoc": " ".join(str(don_thuoc.get("ma_don_thuoc") or "").split()) or None,
        "ten_nguoi_ke_don": " ".join(str(don_thuoc.get("ten_nguoi_ke_don") or "").split()),
        "noi_kham_benh": " ".join(str(don_thuoc.get("noi_kham_benh") or "").split()),
    }
    if not (
        thong_tin["da_kiem_tra_don_thuoc"]
        and thong_tin["ten_nguoi_ke_don"]
        and thong_tin["noi_kham_benh"]
    ):
        raise ValidationError(THONG_BAO_KE_DON)
    ma = thong_tin["ma_don_thuoc"]
    if ma and not re.fullmatch(MA_DON_THUOC, ma):
        raise ValidationError("Mã đơn thuốc gồm 6–30 chữ, số hoặc dấu gạch ngang.")
    if len(thong_tin["ten_nguoi_ke_don"]) > 120 or len(thong_tin["noi_kham_benh"]) > 200:
        raise ValidationError("Tên bác sĩ hoặc cơ sở khám bệnh quá dài.")
    return thong_tin


@transaction.atomic
def ban_tai_quay(
    nguoi,
    chi_nhanh,
    cac_dong,
    *,
    khoa_yeu_cau=None,
    don_hang=None,
    don_thuoc=None,
    phuong_thuc_thanh_toan="tien_mat",
):
    """Lập phiếu bán và xuất kho FEFO.

    Có `don_hang`: xuất đúng các dòng của đơn với giá đã chụp lúc đặt. Đơn nhận tại
    quầy chuyển hoàn thành (khách nhận và trả tiền), đơn giao hàng chuyển đang chuẩn bị.
    Không có đơn: bán trực tiếp theo giá đang áp dụng. `don_thuoc` gồm
    da_kiem_tra_don_thuoc, ma_don_thuoc, ten_nguoi_ke_don, noi_kham_benh và chỉ bắt
    buộc khi phiếu có thuốc kê đơn.
    """
    if phuong_thuc_thanh_toan not in PHUONG_THUC_TAI_QUAY:
        raise ValidationError("Tại quầy chỉ nhận tiền mặt hoặc chuyển khoản.")
    khoa_chi_nhanh(nguoi, chi_nhanh)
    khoa_yeu_cau = str(khoa_yeu_cau or uuid4())
    da_co = PhieuBan.objects.filter(
        khoa_yeu_cau=khoa_yeu_cau, nguoi_lap=nguoi, chi_nhanh=chi_nhanh
    ).first()
    if da_co:
        return da_co
    if don_hang:
        don_hang = DonHang.objects.select_for_update().get(pk=don_hang.pk)
        if don_hang.chi_nhanh_id != chi_nhanh.pk:
            raise ValidationError("Đơn không thuộc chi nhánh bán.")
        da_ban = PhieuBan.objects.filter(don_hang=don_hang).first()
        if da_ban:
            return da_ban
        den = "hoan_thanh" if don_hang.hinh_thuc_nhan == "nhan_tai_quay" else "dang_chuan_bi"
        kiem_tra_chuyen(don_hang, den, nguoi)
        if don_hang.trang_thai == "dang_giu" and don_hang.thoi_diem_het_giu <= timezone.now():
            raise ValidationError("Đơn đã quá hạn giữ.")
        cac_dong = [
            {"thuoc": dong.thuoc, "so_luong": dong.so_luong, "don_gia": dong.don_gia}
            for dong in don_hang.cac_dong.select_related("thuoc")
        ]
    if not cac_dong:
        raise ValidationError("Phiếu bán cần ít nhất một thuốc.")
    cac_thuoc = them_gia_va_anh(
        Thuoc.objects.filter(pk__in=[dong["thuoc"].pk for dong in cac_dong])
    ).in_bulk()
    thong_tin_don = _thong_tin_don_thuoc(
        any(t.la_thuoc_ke_don for t in cac_thuoc.values()), don_thuoc
    )
    phieu = PhieuBan(
        ma_phieu_ban=ma_chung_tu("BH"),
        khoa_yeu_cau=khoa_yeu_cau,
        chi_nhanh=chi_nhanh,
        nguoi_lap=nguoi,
        don_hang=don_hang,
        **thong_tin_don,
    )
    phieu.save()
    for dong in cac_dong:
        thuoc = cac_thuoc[dong["thuoc"].pk]
        luong = doi_ve_co_so(thuoc, dong["so_luong"], dong.get("quy_doi_bao_goi"))
        chi_tiet = ChiTietPhieuBan(
            phieu_ban=phieu,
            thuoc=thuoc,
            ma_thuoc_luc_ban=thuoc.ma_thuoc,
            ten_thuoc_luc_ban=thuoc.ten_thuoc,
            so_luong=luong,
            don_gia=dong.get("don_gia", thuoc.don_gia),
        )
        chi_tiet.full_clean()
        chi_tiet.save()
        for ton, lay in phan_bo_fefo(chi_nhanh, thuoc, luong, bo_qua_don=don_hang):
            thay_doi_ton(ton, -lay)
            PhanBoPhieuBan.objects.create(chi_tiet_phieu_ban=chi_tiet, ton_kho=ton, so_luong=lay)
    if not don_hang or den == "hoan_thanh":
        ghi_ngay(
            loai="thu",
            phuong_thuc=phuong_thuc_thanh_toan,
            so_tien=don_hang.tong_thanh_toan if don_hang else tong_tien_ban(phieu),
            don_hang=don_hang,
            phieu_ban=phieu,
            nguoi=nguoi,
            ghi_chu="Thu tại quầy",
        )
    if don_hang:
        them_cot = ()
        if den == "hoan_thanh":
            don_hang.trang_thai_thanh_toan = "da_thanh_toan"
            them_cot = ("trang_thai_thanh_toan",)
        doi_trang_thai(
            don_hang, den, nguoi, f"Lập phiếu bán {phieu.ma_phieu_ban}", them_cot=them_cot
        )
        bao_doi_trang_thai(don_hang)
    return phieu
