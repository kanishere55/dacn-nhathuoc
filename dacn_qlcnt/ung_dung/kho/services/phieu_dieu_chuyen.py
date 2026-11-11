from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from ung_dung.chung.permissions import kiem_tra_quyen_ghi_chi_nhanh
from ung_dung.chung.van_ban import cat_khoang_trang
from ung_dung.danh_muc.models import ChiNhanh

from ..loi_dong import LoiDongPhieu
from ..models import ChiTietPhieuDieuChuyen, PhieuDieuChuyen, TonKho
from ..quy_tac import don_vi, so
from ..selectors import lay_ton_kha_dung
from .chong_trung import chuan_hoa_khoa, phieu_da_luu
from .giao_dich import doi_ve_co_so, ma_chung_tu, phan_bo_fefo, thay_doi_ton


def _con_ban_duoc(chi_nhanh, thuoc):
    return (
        lay_ton_kha_dung(chi_nhanh=chi_nhanh)
        .filter(lo_thuoc__thuoc=thuoc, kha_dung__gt=0)
        .aggregate(tong=Sum("kha_dung"))["tong"]
        or 0
    )


@transaction.atomic
def dieu_chuyen(nguoi, nguon, dich, cac_dong, ghi_chu="", *, khoa_yeu_cau=None):
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, nguon, "dieu_chuyen.tao")
    if nguon.pk == dich.pk:
        raise ValidationError({"chi_nhanh_dich": "Chi nhánh nhận phải khác chi nhánh chuyển đi."})
    if not cac_dong:
        raise ValidationError("Phiếu điều chuyển cần ít nhất một thuốc.")
    cac_chi_nhanh = list(
        ChiNhanh.objects.select_for_update().filter(pk__in=[nguon.pk, dich.pk]).order_by("pk")
    )
    ngung = [cn.ten_chi_nhanh for cn in cac_chi_nhanh if not cn.dang_hoat_dong]
    if len(cac_chi_nhanh) != 2 or ngung:
        raise ValidationError(f"Chi nhánh đã ngừng hoạt động: {', '.join(ngung)}.")
    list(TonKho.objects.select_for_update().filter(chi_nhanh__in=cac_chi_nhanh).order_by("pk"))
    da_co = phieu_da_luu(
        PhieuDieuChuyen, khoa_yeu_cau, nguoi, chi_nhanh_nguon=nguon, chi_nhanh_dich=dich
    )
    if da_co:
        return da_co
    phieu = PhieuDieuChuyen.objects.create(
        ma_phieu_dieu_chuyen=ma_chung_tu("DC"),
        chi_nhanh_nguon=nguon,
        chi_nhanh_dich=dich,
        nguoi_lap=nguoi,
        ghi_chu=cat_khoang_trang(ghi_chu),
        khoa_yeu_cau=chuan_hoa_khoa(khoa_yeu_cau),
    )
    cac_loi = []
    for i, dong in enumerate(cac_dong):
        thuoc, quy_doi = dong["thuoc"], dong.get("quy_doi_bao_goi")
        if quy_doi and quy_doi.thuoc_id != thuoc.pk:
            cac_loi.append((i, "quy_doi_bao_goi", "Bao gói này không thuộc thuốc đã chọn."))
            continue
        try:
            luong = doi_ve_co_so(thuoc, dong["so_luong"], quy_doi)
        except ValidationError as loi:
            cac_loi.append((i, "so_luong", " ".join(loi.messages)))
            continue
        # Dòng trước đã trừ tồn nguồn, nên số còn bán được tính lại cho từng dòng.
        con = _con_ban_duoc(nguon, thuoc)
        if luong > con:
            cac_loi.append(
                (
                    i,
                    "so_luong",
                    f"{nguon.ten_chi_nhanh} chỉ còn {so(con)} {don_vi(thuoc)} {thuoc.ten_thuoc} "
                    f"chuyển được (đã trừ hàng đang giữ cho khách, lô hết hạn hoặc bị khóa); "
                    f"bạn chuyển {so(luong)} {don_vi(thuoc)}.",
                )
            )
            continue
        for ton, phan in phan_bo_fefo(nguon, thuoc, luong):
            thay_doi_ton(ton, -phan)
            nhan, _ = TonKho.objects.get_or_create(chi_nhanh=dich, lo_thuoc=ton.lo_thuoc)
            thay_doi_ton(nhan, phan)
            ChiTietPhieuDieuChuyen.objects.create(
                phieu_dieu_chuyen=phieu, lo_thuoc=ton.lo_thuoc, so_luong=phan
            )
    if cac_loi:
        raise LoiDongPhieu(cac_loi)
    return phieu
