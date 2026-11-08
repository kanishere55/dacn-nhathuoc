from django.core.exceptions import ValidationError

from ung_dung.kho.services.giao_dich import ma_chung_tu, thay_doi_ton

from ..models import ChiTietPhieuHoanKho, PhanBoPhieuBan, PhieuHoanKho


def hoan_kho(nguoi, phieu_ban, ly_do):
    """Nhập lại đúng các lô đã xuất của phiếu bán. Gọi trong transaction đã khóa kho."""
    if PhieuHoanKho.objects.filter(phieu_ban=phieu_ban).exists():
        raise ValidationError("Phiếu bán này đã được hoàn kho.")
    phieu = PhieuHoanKho.objects.create(
        ma_phieu_hoan_kho=ma_chung_tu("HK"), phieu_ban=phieu_ban, nguoi_lap=nguoi, ly_do=ly_do
    )
    for phan_bo in (
        PhanBoPhieuBan.objects.filter(chi_tiet_phieu_ban__phieu_ban=phieu_ban)
        .select_related("ton_kho")
        .order_by("pk")
    ):
        thay_doi_ton(phan_bo.ton_kho, phan_bo.so_luong)
        ChiTietPhieuHoanKho.objects.create(
            phieu_hoan_kho=phieu, phan_bo_phieu_ban=phan_bo, so_luong=phan_bo.so_luong
        )
    return phieu
