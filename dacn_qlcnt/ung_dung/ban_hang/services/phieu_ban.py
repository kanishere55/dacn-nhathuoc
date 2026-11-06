from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.danh_muc.models import Thuoc
from ung_dung.kho.services.giao_dich import (
    doi_ve_co_so,
    khoa_chi_nhanh,
    ma_chung_tu,
    phan_bo_fefo,
    thay_doi_ton,
)

from ..models import ChiTietDonDatGiu, ChiTietPhieuBan, DonDatGiu, PhanBoPhieuBan, PhieuBan


@transaction.atomic
def ban_tai_quay(nguoi, chi_nhanh, cac_dong, *, khoa_yeu_cau=None, don_dat_giu=None):
    khoa_chi_nhanh(nguoi, chi_nhanh)
    khoa_yeu_cau = str(khoa_yeu_cau or uuid4())
    da_co = PhieuBan.objects.filter(
        khoa_yeu_cau=khoa_yeu_cau, nguoi_lap=nguoi, chi_nhanh=chi_nhanh
    ).first()
    if da_co:
        return da_co
    if don_dat_giu:
        don_dat_giu = DonDatGiu.objects.select_for_update().get(pk=don_dat_giu.pk)
        if don_dat_giu.chi_nhanh_id != chi_nhanh.pk:
            raise ValidationError("Đơn không thuộc chi nhánh bán.")
        da_ban = PhieuBan.objects.filter(don_dat_giu=don_dat_giu).first()
        if da_ban:
            return da_ban
        if don_dat_giu.trang_thai != "dang_giu" or don_dat_giu.thoi_diem_het_giu <= timezone.now():
            raise ValidationError("Đơn không còn hiệu lực giữ.")
        cac_dong = [
            {"thuoc": dong.thuoc, "so_luong": dong.so_luong}
            for dong in ChiTietDonDatGiu.objects.filter(don_dat_giu=don_dat_giu).select_related(
                "thuoc"
            )
        ]
    if not cac_dong:
        raise ValidationError("Phiếu bán cần ít nhất một thuốc.")
    phieu = PhieuBan.objects.create(
        ma_phieu_ban=ma_chung_tu("BH"),
        khoa_yeu_cau=khoa_yeu_cau,
        chi_nhanh=chi_nhanh,
        nguoi_lap=nguoi,
        don_dat_giu=don_dat_giu,
    )
    for dong in cac_dong:
        thuoc = Thuoc.objects.get(pk=dong["thuoc"].pk)
        luong = doi_ve_co_so(thuoc, dong["so_luong"], dong.get("quy_doi_bao_goi"))
        chi_tiet = ChiTietPhieuBan(
            phieu_ban=phieu,
            thuoc=thuoc,
            ma_thuoc_luc_ban=thuoc.ma_thuoc,
            ten_thuoc_luc_ban=thuoc.ten_thuoc,
            so_luong=luong,
            don_gia=thuoc.gia_ban,
        )
        chi_tiet.full_clean()
        chi_tiet.save()
        for ton, lay in phan_bo_fefo(chi_nhanh, thuoc, luong, bo_qua_don=don_dat_giu):
            thay_doi_ton(ton, -lay)
            PhanBoPhieuBan.objects.create(chi_tiet_phieu_ban=chi_tiet, ton_kho=ton, so_luong=lay)
    if don_dat_giu:
        don_dat_giu.trang_thai = "da_nhan"
        don_dat_giu.save(update_fields=["trang_thai"])
    return phieu
