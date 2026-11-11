from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from ung_dung.chung.van_ban import cat_khoang_trang

from ..loi_dong import LoiDongPhieu
from ..models import ChiTietPhieuNhap, ChiTietPhieuTraNhaCungCap, PhieuTraNhaCungCap
from ..quy_tac import don_vi, so
from ..selectors import lay_so_du
from .chong_trung import chuan_hoa_khoa, phieu_da_luu
from .giao_dich import khoa_chi_nhanh, ma_chung_tu, thay_doi_ton


def luong_con_tra(phieu_nhap, lo):
    """(đã nhập theo phiếu, đã trả theo phiếu) của một lô."""
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
    return da_nhap, da_tra


def _loi_dong(phieu_nhap, lo, luong):
    """Câu báo vì sao không trả được, kèm con số để người lập biết sửa thành bao nhiêu."""
    dv = don_vi(lo.thuoc)
    da_nhap, da_tra = luong_con_tra(phieu_nhap, lo)
    if not da_nhap:
        return "lo_thuoc", (
            f"Lô {lo.ma_lo_thuoc} không có trong phiếu {phieu_nhap.ma_phieu_nhap}; chỉ trả được "
            "lô đã nhập theo phiếu này."
        )
    if luong > da_nhap - da_tra:
        return "so_luong", (
            f"Lô {lo.ma_lo_thuoc}: phiếu {phieu_nhap.ma_phieu_nhap} nhập {so(da_nhap)} {dv}, "
            f"đã trả {so(da_tra)} {dv}, chỉ còn trả được {so(da_nhap - da_tra)} {dv}."
        )
    ton = lay_so_du(chi_nhanh=phieu_nhap.chi_nhanh).filter(lo_thuoc=lo).first()
    if ton is None or luong > ton.kha_dung:
        con = ton.so_luong if ton else 0
        giu = ton.dang_giu if ton else 0
        return "so_luong", (
            f"Lô {lo.ma_lo_thuoc}: kho còn {so(con)} {dv}, trong đó {so(giu)} {dv} đang giữ cho "
            f"đơn của khách; chỉ trả được {so(max(con - giu, 0))} {dv}."
        )
    return None, ton


@transaction.atomic
def tra_nha_cung_cap(nguoi, phieu_nhap, cac_dong, ghi_chu="", *, khoa_yeu_cau=None):
    khoa_chi_nhanh(nguoi, phieu_nhap.chi_nhanh, "phieu_tra.tao")
    da_co = phieu_da_luu(PhieuTraNhaCungCap, khoa_yeu_cau, nguoi, phieu_nhap=phieu_nhap)
    if da_co:
        return da_co
    if not cac_dong:
        raise ValidationError("Phiếu trả cần ít nhất một dòng.")
    if not cat_khoang_trang(ghi_chu):
        # Q40: chứng từ xuất trả cần lý do để đối chiếu với nhà cung cấp và khi thanh tra GPP.
        raise ValidationError("Ghi lý do trả để đối chiếu với nhà cung cấp.")
    phieu = PhieuTraNhaCungCap.objects.create(
        ma_phieu_tra_nha_cung_cap=ma_chung_tu("PT"),
        phieu_nhap=phieu_nhap,
        nguoi_lap=nguoi,
        ghi_chu=cat_khoang_trang(ghi_chu),
        khoa_yeu_cau=chuan_hoa_khoa(khoa_yeu_cau),
    )
    cac_loi = []
    # Từng dòng trừ tồn ngay, nên dòng sau (kể cả cùng lô) được kiểm trên số còn lại.
    for i, dong in enumerate(cac_dong):
        lo, luong = dong["lo_thuoc"], dong["so_luong"]
        if not isinstance(luong, int) or isinstance(luong, bool) or luong <= 0:
            cac_loi.append((i, "so_luong", "Lượng trả phải là số nguyên dương."))
            continue
        o_sai, ket_qua = _loi_dong(phieu_nhap, lo, luong)
        if o_sai:
            cac_loi.append((i, o_sai, ket_qua))
            continue
        thay_doi_ton(ket_qua, -luong)
        ChiTietPhieuTraNhaCungCap.objects.create(
            phieu_tra_nha_cung_cap=phieu, lo_thuoc=lo, so_luong=luong
        )
    if cac_loi:
        raise LoiDongPhieu(cac_loi)
    return phieu
