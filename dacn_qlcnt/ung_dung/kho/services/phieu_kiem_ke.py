from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import ChiTietPhieuKiemKe, PhieuKiemKe
from ..quy_tac import don_vi, so
from ..selectors import lay_so_du
from .chong_trung import chuan_hoa_khoa, phieu_da_luu
from .giao_dich import GIOI_HAN_TON, khoa_chi_nhanh, ma_chung_tu, thay_doi_ton


class LoiKiemKe(ValidationError):
    """Lỗi theo từng dòng tồn kho, để màn hình chỉ đúng lô cần sửa.

    `loi_theo_ton`: {id tồn kho: câu báo}. `so_du_moi`: {id tồn kho: số sổ sách hiện tại} của
    các lô vừa có phát sinh, phải đếm lại (Q08); các lô khác giữ nguyên số đã đếm.
    """

    def __init__(self, loi_theo_ton, so_du_moi):
        self.loi_theo_ton = dict(loi_theo_ton)
        self.so_du_moi = dict(so_du_moi)
        super().__init__(list(self.loi_theo_ton.values()))


def ma_don_dang_giu(ton):
    """Mã các đơn đang giữ hàng trên một dòng tồn (cùng điều kiện với lay_so_du)."""
    from ung_dung.ban_hang.models import TRANG_THAI_GIU

    PhanBoDonHang = apps.get_model("ban_hang", "PhanBoDonHang")
    return list(
        PhanBoDonHang.objects.filter(
            ton_kho=ton,
            chi_tiet_don_hang__don_hang__trang_thai__in=TRANG_THAI_GIU,
            chi_tiet_don_hang__don_hang__thoi_diem_het_giu__gt=timezone.now(),
        )
        .order_by("chi_tiet_don_hang__don_hang__ma_don_hang")
        .values_list("chi_tiet_don_hang__don_hang__ma_don_hang", flat=True)
        .distinct()
    )


def _kiem_dong(dong, ton, da_dem):
    """Câu báo nếu dòng không ghi được; kèm số sổ sách mới nếu lô vừa có phát sinh."""
    lo = ton.lo_thuoc
    dv = don_vi(lo.thuoc)
    if ton.pk in da_dem:
        return f"Lô {lo.ma_lo_thuoc} được nhập hai lần; mỗi lô chỉ ghi một số đếm.", None
    da_dem.add(ton.pk)
    if ton.so_luong != dong["so_luong_so_sach"]:
        return (
            f"Lô {lo.ma_lo_thuoc}: lúc mở trang sổ sách là {so(dong['so_luong_so_sach'])} {dv}, "
            f"nay là {so(ton.so_luong)} {dv} vì vừa có bán, nhập hoặc chuyển hàng. "
            "Hãy đếm lại lô này rồi lưu."
        ), ton.so_luong
    luong = dong["so_luong_thuc_te"]
    if not isinstance(luong, int) or isinstance(luong, bool) or luong < 0:
        return f"Lô {lo.ma_lo_thuoc}: số đếm phải là số nguyên từ 0 trở lên.", None
    if luong > GIOI_HAN_TON:
        return f"Lô {lo.ma_lo_thuoc}: số đếm vượt giới hạn của kho.", None
    if luong < ton.dang_giu:
        cac_don = ", ".join(ma_don_dang_giu(ton)) or "của khách"
        return (
            f"Lô {lo.ma_lo_thuoc}: đang giữ {so(ton.dang_giu)} {dv} cho đơn {cac_don} nhưng "
            f"chỉ đếm được {so(luong)} {dv}. Hãy giao hoặc hủy các đơn đó (hoặc báo quản lý) "
            "trước, rồi kiểm kê lại lô này."
        ), None
    return None, None


@transaction.atomic
def kiem_ke(nguoi, chi_nhanh, cac_dong, ghi_chu="", *, khoa_yeu_cau=None):
    """Ghi số đếm và đưa tồn về đúng số đếm; chỉ lưu khi mọi dòng khớp số dư lúc mở (Q08)."""
    khoa_chi_nhanh(nguoi, chi_nhanh, "kiem_ke.tao")
    da_co = phieu_da_luu(PhieuKiemKe, khoa_yeu_cau, nguoi, chi_nhanh=chi_nhanh)
    if da_co:
        return da_co
    if not cac_dong:
        raise ValidationError(
            "Chưa nhập số đếm cho lô nào. Nhập số đếm ở các lô đã đếm rồi bấm lưu."
        )
    ton_theo_id = lay_so_du(chi_nhanh=chi_nhanh).in_bulk([dong["ton_kho"].pk for dong in cac_dong])
    loi_theo_ton, so_du_moi, da_dem = {}, {}, set()
    for dong in cac_dong:
        ton = ton_theo_id.get(dong["ton_kho"].pk)
        if ton is None:
            loi_theo_ton[dong["ton_kho"].pk] = "Lô này không thuộc kho đang kiểm kê."
            continue
        cau, moi = _kiem_dong(dong, ton, da_dem)
        if cau:
            loi_theo_ton[ton.pk] = cau
        if moi is not None:
            so_du_moi[ton.pk] = moi
    if loi_theo_ton:
        raise LoiKiemKe(loi_theo_ton, so_du_moi)
    phieu = PhieuKiemKe.objects.create(
        ma_phieu_kiem_ke=ma_chung_tu("KK"),
        chi_nhanh=chi_nhanh,
        nguoi_lap=nguoi,
        ghi_chu=cat_khoang_trang(ghi_chu),
        khoa_yeu_cau=chuan_hoa_khoa(khoa_yeu_cau),
    )
    for dong in cac_dong:
        ton = ton_theo_id[dong["ton_kho"].pk]
        luong = dong["so_luong_thuc_te"]
        ChiTietPhieuKiemKe.objects.create(
            phieu_kiem_ke=phieu,
            lo_thuoc=ton.lo_thuoc,
            so_luong_so_sach=ton.so_luong,
            so_luong_thuc_te=luong,
        )
        thay_doi_ton(ton, luong - ton.so_luong)
    return phieu
