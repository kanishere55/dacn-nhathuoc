"""Đánh giá thuốc: chỉ khách đã nhận thuốc qua đơn hoàn thành mới được chấm sao."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_vai_tro

from ..models import DanhGiaThuoc


def da_mua(nguoi, thuoc):
    from ung_dung.ban_hang.models import ChiTietDonHang

    return ChiTietDonHang.objects.filter(
        don_hang__khach_hang=nguoi, don_hang__trang_thai="hoan_thanh", thuoc=thuoc
    ).exists()


@transaction.atomic
def luu_danh_gia(nguoi, thuoc, so_sao, noi_dung=""):
    kiem_tra_vai_tro(nguoi, "khach_hang")
    if not da_mua(nguoi, thuoc):
        raise ValidationError("Chỉ khách đã nhận thuốc này qua đơn hoàn thành mới đánh giá được.")
    so_sao = int(so_sao)
    if not 1 <= so_sao <= 5:
        raise ValidationError("Chọn từ 1 đến 5 sao.")
    danh_gia, _ = DanhGiaThuoc.objects.update_or_create(
        thuoc=thuoc,
        khach_hang=nguoi,
        defaults={
            "so_sao": so_sao,
            "noi_dung_danh_gia": (noi_dung or "").strip()[:1000],
            "thoi_diem_tao": timezone.now(),
        },
    )
    return danh_gia


def tom_tat_danh_gia(thuoc):
    cac_danh_gia = DanhGiaThuoc.objects.filter(thuoc=thuoc, dang_hien_thi=True)
    tong = cac_danh_gia.aggregate(trung_binh=Avg("so_sao"), so_luong=Count("pk"))
    dem = dict(cac_danh_gia.values_list("so_sao").annotate(n=Count("pk")))
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
