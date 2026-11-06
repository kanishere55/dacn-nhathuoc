from django.core.exceptions import ValidationError
from django.db import transaction

from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import ChiTietPhieuKiemKe, PhieuKiemKe
from ..selectors import lay_so_du
from .giao_dich import khoa_chi_nhanh, ma_chung_tu, thay_doi_ton


@transaction.atomic
def kiem_ke(nguoi, chi_nhanh, cac_dong, ghi_chu=""):
    khoa_chi_nhanh(nguoi, chi_nhanh, quan_ly=True)
    if not cac_dong:
        raise ValidationError("Cần ít nhất một dòng kiểm kê.")
    phieu = PhieuKiemKe.objects.create(
        ma_phieu_kiem_ke=ma_chung_tu("KK"),
        chi_nhanh=chi_nhanh,
        nguoi_lap=nguoi,
        ghi_chu=cat_khoang_trang(ghi_chu),
    )
    da_dem = set()
    for dong in cac_dong:
        ton = lay_so_du(chi_nhanh=chi_nhanh).filter(pk=dong["ton_kho"].pk).first()
        if ton is None:
            raise ValidationError("Có dòng kiểm kê không thuộc chi nhánh đã chọn.")
        if ton.pk in da_dem or ton.so_luong != dong["so_luong_so_sach"]:
            raise ValidationError("Dòng bị trùng hoặc số dư đã thay đổi. Hãy mở lại và đếm lại.")
        da_dem.add(ton.pk)
        luong = dong["so_luong_thuc_te"]
        if not isinstance(luong, int) or isinstance(luong, bool) or luong < ton.dang_giu:
            raise ValidationError("Lượng đếm không được âm hoặc nhỏ hơn lượng đang giữ.")
        ChiTietPhieuKiemKe.objects.create(
            phieu_kiem_ke=phieu,
            lo_thuoc=ton.lo_thuoc,
            so_luong_so_sach=ton.so_luong,
            so_luong_thuc_te=luong,
        )
        thay_doi_ton(ton, luong - ton.so_luong)
    return phieu
