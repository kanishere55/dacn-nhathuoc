from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import ChiTietPhieuNhap, ChiTietPhieuTraNhaCungCap, PhieuTraNhaCungCap
from ..selectors import lay_so_du
from .giao_dich import khoa_chi_nhanh, ma_chung_tu, thay_doi_ton


@transaction.atomic
def tra_nha_cung_cap(nguoi, phieu_nhap, cac_dong, ghi_chu=""):
    khoa_chi_nhanh(nguoi, phieu_nhap.chi_nhanh, "phieu_tra.tao")
    if not cac_dong:
        raise ValidationError("Phiếu trả cần ít nhất một dòng.")
    phieu = PhieuTraNhaCungCap.objects.create(
        ma_phieu_tra_nha_cung_cap=ma_chung_tu("PT"),
        phieu_nhap=phieu_nhap,
        nguoi_lap=nguoi,
        ghi_chu=cat_khoang_trang(ghi_chu),
    )
    for dong in cac_dong:
        lo, luong = dong["lo_thuoc"], dong["so_luong"]
        if not isinstance(luong, int) or isinstance(luong, bool) or luong <= 0:
            raise ValidationError("Lượng trả phải là số nguyên dương.")
        da_nhap = (
            ChiTietPhieuNhap.objects.filter(phieu_nhap=phieu_nhap, lo_thuoc=lo).aggregate(
                tong=Sum("so_luong")
            )["tong"]
            or 0
        )
        da_tra = (
            ChiTietPhieuTraNhaCungCap.objects.filter(
                phieu_tra_nha_cung_cap__phieu_nhap=phieu_nhap, lo_thuoc=lo
            ).aggregate(tong=Sum("so_luong"))["tong"]
            or 0
        )
        ton = lay_so_du(chi_nhanh=phieu_nhap.chi_nhanh).filter(lo_thuoc=lo).first()
        if luong > da_nhap - da_tra or not ton or luong > ton.kha_dung:
            raise ValidationError("Lượng trả vượt lượng còn được trả hoặc đang được giữ.")
        thay_doi_ton(ton, -luong)
        ChiTietPhieuTraNhaCungCap.objects.create(
            phieu_tra_nha_cung_cap=phieu, lo_thuoc=lo, so_luong=luong
        )
    return phieu
