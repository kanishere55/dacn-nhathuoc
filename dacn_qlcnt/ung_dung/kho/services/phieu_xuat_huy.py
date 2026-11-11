from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.van_ban import cat_khoang_trang

from ..loi_dong import LoiDongPhieu
from ..models import LOAI_XUAT_HUY, ChiTietPhieuXuatHuy, PhieuXuatHuy
from ..quy_tac import don_vi, so
from ..selectors import lay_so_du
from .chong_trung import chuan_hoa_khoa, phieu_da_luu
from .giao_dich import khoa_chi_nhanh, ma_chung_tu, thay_doi_ton


def _loi_dong(chi_nhanh, loai_xuat_huy, lo, luong, hom_nay):
    if isinstance(luong, bool) or not isinstance(luong, int) or luong <= 0:
        return "so_luong", "Lượng hủy phải là số nguyên dương.", None
    # Lô còn được bán hết ngày hết hạn (Q04), nên chỉ coi là hết hạn từ ngày hôm sau.
    if loai_xuat_huy == "het_han" and lo.ngay_het_han >= hom_nay:
        return (
            "lo_thuoc",
            f"Lô {lo.ma_lo_thuoc} còn hạn đến {lo.ngay_het_han:%d/%m/%Y}; chưa hết hạn nên hãy "
            "chọn lý do hư hỏng (hoặc thu hồi nếu lô đang bị khóa bán).",
            None,
        )
    if loai_xuat_huy == "thu_hoi" and lo.duoc_phep_ban:
        return (
            "lo_thuoc",
            f"Lô {lo.ma_lo_thuoc} đang được bán bình thường. Lý do thu hồi chỉ dùng cho lô đã bị "
            "khóa bán theo thông báo thu hồi.",
            None,
        )
    # Tính lại sau mỗi dòng để hai dòng cùng lô không vượt tồn.
    ton = lay_so_du(chi_nhanh=chi_nhanh).filter(lo_thuoc=lo).first()
    dv = don_vi(lo.thuoc)
    if ton is None or not ton.so_luong:
        return (
            "lo_thuoc",
            f"Lô {lo.ma_lo_thuoc} không còn hàng ở {chi_nhanh.ten_chi_nhanh}; kiểm tra lại chi "
            "nhánh đã chọn.",
            None,
        )
    if luong > ton.kha_dung:
        return (
            "so_luong",
            f"Lô {lo.ma_lo_thuoc}: kho còn {so(ton.so_luong)} {dv}, trong đó {so(ton.dang_giu)} "
            f"{dv} đang giữ cho đơn của khách; chỉ hủy được tối đa {so(ton.kha_dung)} {dv}.",
            None,
        )
    return None, None, ton


@transaction.atomic
def xuat_huy(nguoi, chi_nhanh, loai_xuat_huy, cac_dong, ghi_chu="", *, khoa_yeu_cau=None):
    khoa_chi_nhanh(nguoi, chi_nhanh, "xuat_huy.tao")
    da_co = phieu_da_luu(PhieuXuatHuy, khoa_yeu_cau, nguoi, chi_nhanh=chi_nhanh)
    if da_co:
        return da_co
    if loai_xuat_huy not in dict(LOAI_XUAT_HUY):
        raise ValidationError("Lý do xuất hủy không hợp lệ.")
    if not cac_dong:
        raise ValidationError("Phiếu xuất hủy cần ít nhất một dòng.")
    ghi_chu = cat_khoang_trang(ghi_chu)
    if loai_xuat_huy == "hu_hong" and not ghi_chu:
        raise ValidationError(
            {"ghi_chu": "Hàng hư hỏng cần mô tả tình trạng và số biên bản trong ghi chú."}
        )
    if loai_xuat_huy == "thu_hoi" and not ghi_chu:
        raise ValidationError(
            {"ghi_chu": "Hủy hàng thu hồi cần ghi số văn bản thu hồi và số biên bản trong ghi chú."}
        )
    phieu = PhieuXuatHuy.objects.create(
        ma_phieu_xuat_huy=ma_chung_tu("PX"),
        chi_nhanh=chi_nhanh,
        nguoi_lap=nguoi,
        loai_xuat_huy=loai_xuat_huy,
        ghi_chu=ghi_chu,
        khoa_yeu_cau=chuan_hoa_khoa(khoa_yeu_cau),
    )
    hom_nay = timezone.localdate()
    cac_loi = []
    for i, dong in enumerate(cac_dong):
        lo, luong = dong["lo_thuoc"], dong["so_luong"]
        o_sai, cau, ton = _loi_dong(chi_nhanh, loai_xuat_huy, lo, luong, hom_nay)
        if o_sai:
            cac_loi.append((i, o_sai, cau))
            continue
        thay_doi_ton(ton, -luong)
        ChiTietPhieuXuatHuy.objects.create(phieu_xuat_huy=phieu, lo_thuoc=lo, so_luong=luong)
    if cac_loi:
        raise LoiDongPhieu(cac_loi)
    return phieu
