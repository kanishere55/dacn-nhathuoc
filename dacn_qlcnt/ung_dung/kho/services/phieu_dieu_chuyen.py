from django.core.exceptions import ValidationError
from django.db import transaction

from ung_dung.chung.permissions import kiem_tra_quyen_ghi_chi_nhanh
from ung_dung.chung.van_ban import cat_khoang_trang
from ung_dung.danh_muc.models import ChiNhanh

from ..models import ChiTietPhieuDieuChuyen, PhieuDieuChuyen, TonKho
from .giao_dich import doi_ve_co_so, ma_chung_tu, phan_bo_fefo, thay_doi_ton


@transaction.atomic
def dieu_chuyen(nguoi, nguon, dich, cac_dong, ghi_chu=""):
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, nguon, quan_ly=True)
    if nguon.pk == dich.pk or not cac_dong:
        raise ValidationError("Cần hai chi nhánh khác nhau và thuốc cần chuyển.")
    cac_chi_nhanh = list(
        ChiNhanh.objects.select_for_update().filter(pk__in=[nguon.pk, dich.pk]).order_by("pk")
    )
    if len(cac_chi_nhanh) != 2 or not all(muc.dang_hoat_dong for muc in cac_chi_nhanh):
        raise ValidationError("Chi nhánh đã ngừng hoạt động.")
    list(TonKho.objects.select_for_update().filter(chi_nhanh__in=cac_chi_nhanh).order_by("pk"))
    phieu = PhieuDieuChuyen.objects.create(
        ma_phieu_dieu_chuyen=ma_chung_tu("DC"),
        chi_nhanh_nguon=nguon,
        chi_nhanh_dich=dich,
        nguoi_lap=nguoi,
        ghi_chu=cat_khoang_trang(ghi_chu),
    )
    for dong in cac_dong:
        thuoc = dong["thuoc"]
        for ton, luong in phan_bo_fefo(
            nguon, thuoc, doi_ve_co_so(thuoc, dong["so_luong"], dong.get("quy_doi_bao_goi"))
        ):
            thay_doi_ton(ton, -luong)
            nhan, _ = TonKho.objects.get_or_create(chi_nhanh=dich, lo_thuoc=ton.lo_thuoc)
            thay_doi_ton(nhan, luong)
            ChiTietPhieuDieuChuyen.objects.create(
                phieu_dieu_chuyen=phieu, lo_thuoc=ton.lo_thuoc, so_luong=luong
            )
    return phieu
