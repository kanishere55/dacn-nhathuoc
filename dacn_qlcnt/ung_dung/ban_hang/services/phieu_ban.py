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

from ..models import ChiTietPhieuBan, DonHang, PhanBoPhieuBan, PhieuBan
from .thong_bao_don import bao_doi_trang_thai
from .trang_thai import doi_trang_thai, kiem_tra_chuyen

THONG_BAO_KE_DON = (
    "Phiếu có thuốc kê đơn: dược sĩ phải kiểm tra đơn thuốc của bác sĩ và đánh dấu đã kiểm tra."
)


@transaction.atomic
def ban_tai_quay(
    nguoi,
    chi_nhanh,
    cac_dong,
    *,
    khoa_yeu_cau=None,
    don_hang=None,
    da_kiem_tra_don_thuoc=False,
):
    """Lập phiếu bán và xuất kho FEFO.

    Có `don_hang`: xuất đúng các dòng của đơn với giá đã chụp lúc đặt. Đơn nhận tại
    quầy chuyển hoàn thành (khách nhận và trả tiền), đơn giao hàng chuyển đang chuẩn bị.
    Không có đơn: bán trực tiếp theo giá đang áp dụng.
    """
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
    if any(t.la_thuoc_ke_don for t in cac_thuoc.values()) and not da_kiem_tra_don_thuoc:
        raise ValidationError(THONG_BAO_KE_DON)
    phieu = PhieuBan.objects.create(
        ma_phieu_ban=ma_chung_tu("BH"),
        khoa_yeu_cau=khoa_yeu_cau,
        chi_nhanh=chi_nhanh,
        nguoi_lap=nguoi,
        don_hang=don_hang,
        da_kiem_tra_don_thuoc=da_kiem_tra_don_thuoc,
    )
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
