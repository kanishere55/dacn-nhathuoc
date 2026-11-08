from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import connection

from ung_dung.chung.permissions import kiem_tra_quyen_ghi_chi_nhanh
from ung_dung.danh_muc.models import ChiNhanh

from ..models import TonKho
from ..selectors import lay_ton_kha_dung


def ma_chung_tu(tien_to):
    return tien_to + uuid4().hex[:20].upper()


def khoa_chi_nhanh(nguoi, chi_nhanh, *, quan_ly=False):
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, chi_nhanh, quan_ly=quan_ly)
    return khoa_kho(chi_nhanh)


def khoa_kho(chi_nhanh, *, cho_phep_ngung=False):
    if not connection.in_atomic_block:
        raise RuntimeError("Khóa kho phải nằm trong transaction.atomic.")
    chi_nhanh = ChiNhanh.objects.select_for_update().get(pk=chi_nhanh.pk)
    if not chi_nhanh.dang_hoat_dong and not cho_phep_ngung:
        raise ValidationError("Chi nhánh đã ngừng hoạt động.")
    list(TonKho.objects.select_for_update().filter(chi_nhanh=chi_nhanh).order_by("pk"))
    return chi_nhanh


def phan_bo_fefo(chi_nhanh, thuoc, so_luong, *, bo_qua_don=None):
    if isinstance(so_luong, bool) or not isinstance(so_luong, int) or so_luong <= 0:
        raise ValidationError("Số lượng phải là số nguyên dương.")
    con_lai = so_luong
    phan_bo = []
    for ton in (
        lay_ton_kha_dung(chi_nhanh=chi_nhanh, bo_qua_don=bo_qua_don)
        .filter(lo_thuoc__thuoc=thuoc, kha_dung__gt=0)
        .order_by("lo_thuoc__ngay_het_han", "lo_thuoc_id")
    ):
        lay = min(con_lai, ton.kha_dung)
        phan_bo.append((ton, lay))
        con_lai -= lay
        if not con_lai:
            return phan_bo
    raise ValidationError(f"Không đủ tồn khả dụng cho {thuoc.ten_thuoc}.")


def thay_doi_ton(ton, chenhlech):
    ton.so_luong += chenhlech
    ton.full_clean()
    ton.save(update_fields=["so_luong"])


def doi_ve_co_so(thuoc, so_luong, quy_doi=None):
    if isinstance(so_luong, bool) or not isinstance(so_luong, int) or so_luong <= 0:
        raise ValidationError("Số lượng phải là số nguyên dương.")
    if quy_doi and quy_doi.thuoc_id != thuoc.pk:
        raise ValidationError("Bao gói không thuộc thuốc đã chọn.")
    so_luong_co_so = so_luong * (quy_doi.he_so if quy_doi else 1)
    if so_luong_co_so > 2147483647:
        raise ValidationError("Số lượng sau quy đổi vượt giới hạn của kho.")
    return so_luong_co_so
