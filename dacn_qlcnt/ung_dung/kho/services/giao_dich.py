import secrets

from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_quyen_ghi_chi_nhanh
from ung_dung.danh_muc.models import ChiNhanh

from ..models import TonKho
from ..selectors import lay_ton_kha_dung, luong_ban_duoc

# Bảng chữ Crockford base32: bỏ I, L, O, U để đọc qua điện thoại không nhầm với 1, 0, V.
CHU_MA = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ma_chung_tu(tien_to):
    """Mã ngắn đọc được: BH-261110-7KQ2XM (loại, ngày lập yymmdd, 6 ký tự ngẫu nhiên).

    32^6 ≈ 1 tỷ tổ hợp mỗi loại mỗi ngày; cột mã có ràng buộc duy nhất làm lớp bảo vệ cuối.
    """
    ngau_nhien = "".join(secrets.choice(CHU_MA) for _ in range(6))
    return f"{tien_to}-{timezone.localdate():%y%m%d}-{ngau_nhien}"


def khoa_chi_nhanh(nguoi, chi_nhanh, quyen):
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, chi_nhanh, quyen)
    return khoa_kho(chi_nhanh)


def khoa_kho(chi_nhanh, *, cho_phep_ngung=False):
    if not connection.in_atomic_block:
        raise RuntimeError("Khóa kho phải nằm trong transaction.atomic.")
    chi_nhanh = ChiNhanh.objects.select_for_update().get(pk=chi_nhanh.pk)
    if not chi_nhanh.dang_hoat_dong and not cho_phep_ngung:
        raise ValidationError("Chi nhánh đã ngừng hoạt động.")
    list(TonKho.objects.select_for_update().filter(chi_nhanh=chi_nhanh).order_by("pk"))
    return chi_nhanh


def _so(luong):
    return f"{luong:,}".replace(",", ".")


def phan_bo_fefo(chi_nhanh, thuoc, so_luong, *, bo_qua_don=None, con_han_den=None):
    """Chọn lô theo FEFO (hết hạn trước xuất trước) cho `so_luong` đơn vị cơ sở.

    `con_han_den`: chỉ lấy lô còn hạn tới ngày này (giữ hàng tới hết hạn giữ của đơn đặt
    giữ). Tổng lấy được không vượt lượng bán được của mọi lô trừ phần giữ mồ côi của
    đơn khác (xem lay_giu_mo_coi), để không lấy mất hàng đã hứa.
    """
    if isinstance(so_luong, bool) or not isinstance(so_luong, int) or so_luong <= 0:
        raise ValidationError("Số lượng phải là số nguyên dương.")
    con_ban_duoc = luong_ban_duoc(
        [chi_nhanh], [thuoc.pk], con_han_den=con_han_den, bo_qua_don=bo_qua_don
    ).get((chi_nhanh.pk, thuoc.pk), 0)
    if con_ban_duoc < so_luong:
        don_vi = getattr(getattr(thuoc, "don_vi_tinh", None), "ten_don_vi_tinh", "").lower()
        han = (
            f" (chỉ tính lô còn hạn đến {con_han_den:%d/%m/%Y})"
            if con_han_den and con_han_den > timezone.localdate()
            else ""
        )
        don_vi = f" {don_vi}" if don_vi else ""
        raise ValidationError(
            f"Không đủ hàng cho {thuoc.ten_thuoc}: cần {_so(so_luong)}{don_vi}, "
            f"chi nhánh chỉ còn bán được {_so(con_ban_duoc)}{han}."
        )
    con_lai = so_luong
    phan_bo = []
    for ton in (
        lay_ton_kha_dung(chi_nhanh=chi_nhanh, bo_qua_don=bo_qua_don, con_han_den=con_han_den)
        .filter(lo_thuoc__thuoc=thuoc, kha_dung__gt=0)
        .order_by("lo_thuoc__ngay_het_han", "lo_thuoc_id")
    ):
        lay = min(con_lai, ton.kha_dung)
        phan_bo.append((ton, lay))
        con_lai -= lay
        if not con_lai:
            return phan_bo
    raise ValidationError(f"Không đủ hàng cho {thuoc.ten_thuoc}.")


GIOI_HAN_TON = 2147483647  # cột so_luong kiểu INTEGER


def thay_doi_ton(ton, chenhlech):
    moi = ton.so_luong + chenhlech
    if moi < 0:
        raise ValidationError(f"Tồn lô {ton.lo_thuoc.ma_lo_thuoc} không đủ cho thao tác này.")
    if moi > GIOI_HAN_TON:
        raise ValidationError(
            f"Tồn lô {ton.lo_thuoc.ma_lo_thuoc} sau thao tác vượt giới hạn {GIOI_HAN_TON:,}.".replace(
                ",", "."
            )
        )
    ton.so_luong = moi
    ton.full_clean()
    ton.save(update_fields=["so_luong"])


def doi_ve_co_so(thuoc, so_luong, quy_doi=None):
    if isinstance(so_luong, bool) or not isinstance(so_luong, int) or so_luong <= 0:
        raise ValidationError("Số lượng phải là số nguyên dương.")
    if quy_doi and quy_doi.thuoc_id != thuoc.pk:
        raise ValidationError("Bao gói không thuộc thuốc đã chọn.")
    so_luong_co_so = so_luong * (quy_doi.he_so if quy_doi else 1)
    if so_luong_co_so > GIOI_HAN_TON:
        raise ValidationError("Số lượng sau quy đổi vượt giới hạn của kho.")
    return so_luong_co_so
