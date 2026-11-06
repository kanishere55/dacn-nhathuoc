import re

from django.core.exceptions import ValidationError
from django.db import transaction

from ung_dung.chung.ten_csdl import MA_NGHIEP_VU
from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import ChiTietPhieuNhap, LoThuoc, PhieuNhap, TonKho
from .giao_dich import doi_ve_co_so, khoa_chi_nhanh, ma_chung_tu, thay_doi_ton


@transaction.atomic
def nhap_hang(nguoi, chi_nhanh, nha_cung_cap, cac_dong, ghi_chu=""):
    khoa_chi_nhanh(nguoi, chi_nhanh)
    if not nha_cung_cap.dang_hoat_dong or not cac_dong:
        raise ValidationError("Cần nhà cung cấp đang hoạt động và ít nhất một dòng nhập.")
    phieu = PhieuNhap.objects.create(
        ma_phieu_nhap=ma_chung_tu("PN"),
        chi_nhanh=chi_nhanh,
        nha_cung_cap=nha_cung_cap,
        nguoi_lap=nguoi,
        ghi_chu=cat_khoang_trang(ghi_chu),
    )
    for dong in cac_dong:
        thuoc = dong["thuoc"]
        ma_lo = cat_khoang_trang(dong["ma_lo_thuoc"])
        if not re.fullmatch(MA_NGHIEP_VU, ma_lo):
            raise ValidationError("Mã lô gồm tối đa 32 chữ hoa, số, gạch ngang hoặc gạch dưới.")
        if not thuoc.dang_hoat_dong:
            raise ValidationError("Thuốc đã ngừng hoạt động.")
        lo, _ = LoThuoc.objects.get_or_create(
            thuoc=thuoc,
            ma_lo_thuoc=ma_lo,
            defaults={"ngay_het_han": dong["ngay_het_han"]},
        )
        if lo.ngay_het_han != dong["ngay_het_han"]:
            raise ValidationError("Cùng thuốc/mã lô không được có hai hạn khác nhau.")
        lo.full_clean()
        luong = doi_ve_co_so(thuoc, dong["so_luong"], dong.get("quy_doi_bao_goi"))
        chi_tiet = ChiTietPhieuNhap(
            phieu_nhap=phieu, lo_thuoc=lo, so_luong=luong, don_gia=dong["don_gia"]
        )
        chi_tiet.full_clean()
        chi_tiet.save()
        ton, _ = TonKho.objects.get_or_create(chi_nhanh=chi_nhanh, lo_thuoc=lo)
        thay_doi_ton(ton, luong)
    return phieu
