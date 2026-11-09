from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import LOAI_XUAT_HUY, ChiTietPhieuXuatHuy, PhieuXuatHuy
from ..selectors import lay_so_du
from .giao_dich import khoa_chi_nhanh, ma_chung_tu, thay_doi_ton


@transaction.atomic
def xuat_huy(nguoi, chi_nhanh, loai_xuat_huy, cac_dong, ghi_chu=""):
    khoa_chi_nhanh(nguoi, chi_nhanh, quan_ly=True)
    if loai_xuat_huy not in dict(LOAI_XUAT_HUY):
        raise ValidationError("Lý do xuất hủy không hợp lệ.")
    if not cac_dong:
        raise ValidationError("Phiếu xuất hủy cần ít nhất một dòng.")
    ghi_chu = cat_khoang_trang(ghi_chu)
    if loai_xuat_huy == "hu_hong" and not ghi_chu:
        raise ValidationError("Hàng hư hỏng cần mô tả tình trạng trong ghi chú.")
    phieu = PhieuXuatHuy.objects.create(
        ma_phieu_xuat_huy=ma_chung_tu("PX"),
        chi_nhanh=chi_nhanh,
        nguoi_lap=nguoi,
        loai_xuat_huy=loai_xuat_huy,
        ghi_chu=ghi_chu,
    )
    hom_nay = timezone.localdate()
    for dong in cac_dong:
        lo, luong = dong["lo_thuoc"], dong["so_luong"]
        if isinstance(luong, bool) or not isinstance(luong, int) or luong <= 0:
            raise ValidationError("Lượng hủy phải là số nguyên dương.")
        # Lô còn được bán hết ngày hết hạn (Q04), nên chỉ coi là hết hạn từ ngày hôm sau.
        if loai_xuat_huy == "het_han" and lo.ngay_het_han >= hom_nay:
            raise ValidationError(f"Lô {lo.ma_lo_thuoc} chưa hết hạn, hãy chọn lý do hư hỏng.")
        # Tính lại sau mỗi dòng để hai dòng cùng lô không vượt tồn.
        ton = lay_so_du(chi_nhanh=chi_nhanh).filter(lo_thuoc=lo).first()
        if not ton or luong > ton.kha_dung:
            raise ValidationError(
                f"Lô {lo.ma_lo_thuoc}: lượng hủy vượt tồn khả dụng hoặc chạm phần đang giữ cho đơn."
            )
        thay_doi_ton(ton, -luong)
        ChiTietPhieuXuatHuy.objects.create(phieu_xuat_huy=phieu, lo_thuoc=lo, so_luong=luong)
    return phieu
