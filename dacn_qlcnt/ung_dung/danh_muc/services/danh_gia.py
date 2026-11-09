"""Đánh giá thuốc và chi nhánh: chỉ khách có đơn hoàn thành mới được chấm sao."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_vai_tro
from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import DanhGiaChiNhanh, DanhGiaThuoc


def da_mua(nguoi, thuoc):
    from ung_dung.ban_hang.models import ChiTietDonHang

    return ChiTietDonHang.objects.filter(
        don_hang__khach_hang=nguoi, don_hang__trang_thai="hoan_thanh", thuoc=thuoc
    ).exists()


def da_mua_tai_chi_nhanh(nguoi, chi_nhanh):
    from ung_dung.ban_hang.models import DonHang

    return DonHang.objects.filter(
        khach_hang=nguoi, chi_nhanh=chi_nhanh, trang_thai="hoan_thanh"
    ).exists()


def _kiem_tra_noi_dung(so_sao, noi_dung):
    so_sao = int(so_sao)
    if not 1 <= so_sao <= 5:
        raise ValidationError("Chọn từ 1 đến 5 sao.")
    # Cắt cả ký tự vô hình để không vướng CHECK da_cat_khoang_trang của CSDL.
    return so_sao, cat_khoang_trang(noi_dung or "")[:1000].rstrip()


@transaction.atomic
def luu_danh_gia(nguoi, thuoc, so_sao, noi_dung=""):
    kiem_tra_vai_tro(nguoi, "khach_hang")
    if not da_mua(nguoi, thuoc):
        raise ValidationError("Chỉ khách đã nhận thuốc này qua đơn hoàn thành mới đánh giá được.")
    so_sao, noi_dung = _kiem_tra_noi_dung(so_sao, noi_dung)
    danh_gia, _ = DanhGiaThuoc.objects.update_or_create(
        thuoc=thuoc,
        khach_hang=nguoi,
        defaults={"so_sao": so_sao, "noi_dung_danh_gia": noi_dung, "thoi_diem_tao": timezone.now()},
    )
    return danh_gia


@transaction.atomic
def luu_danh_gia_chi_nhanh(nguoi, chi_nhanh, so_sao, noi_dung=""):
    kiem_tra_vai_tro(nguoi, "khach_hang")
    if not da_mua_tai_chi_nhanh(nguoi, chi_nhanh):
        raise ValidationError("Chỉ khách có đơn hoàn thành tại chi nhánh này mới đánh giá được.")
    so_sao, noi_dung = _kiem_tra_noi_dung(so_sao, noi_dung)
    danh_gia, _ = DanhGiaChiNhanh.objects.update_or_create(
        chi_nhanh=chi_nhanh,
        khach_hang=nguoi,
        defaults={"so_sao": so_sao, "noi_dung_danh_gia": noi_dung, "thoi_diem_tao": timezone.now()},
    )
    return danh_gia


def _tom_tat(cac_danh_gia):
    tong = cac_danh_gia.aggregate(trung_binh=Avg("so_sao"), so_luong=Count("pk"))
    dem = dict(cac_danh_gia.order_by().values_list("so_sao").annotate(n=Count("pk")))
    so_luong = tong["so_luong"] or 0
    return {
        "trung_binh": round(tong["trung_binh"] or 0, 1),
        "sao_tron": round(tong["trung_binh"] or 0),
        "so_luong": so_luong,
        "phan_bo": [
            (sao, dem.get(sao, 0), round(100 * dem.get(sao, 0) / so_luong) if so_luong else 0)
            for sao in range(5, 0, -1)
        ],
        "moi_nhat": cac_danh_gia.select_related("khach_hang")[:8],
    }


def tom_tat_danh_gia(thuoc):
    return _tom_tat(DanhGiaThuoc.objects.filter(thuoc=thuoc, dang_hien_thi=True))


def tom_tat_danh_gia_chi_nhanh(chi_nhanh):
    return _tom_tat(DanhGiaChiNhanh.objects.filter(chi_nhanh=chi_nhanh, dang_hien_thi=True))
