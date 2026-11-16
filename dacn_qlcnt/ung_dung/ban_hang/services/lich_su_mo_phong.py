"""Sinh lịch sử bán mô phỏng nhiều ngày qua đúng nghiệp vụ nhập hàng và bán tại quầy.

Mỗi chi nhánh lập một phiếu nhập lô riêng (mã LS-...) với hạn dùng sớm hơn mọi lô đang
còn hàng của cùng thuốc, nên FEFO xuất từ lô này trước và không đụng tồn kho hiện có.
Số lượng nhập bằng đúng tổng sẽ bán, lô về 0 sau khi chạy. Mỗi phiếu bán đi qua
ban_tai_quay (khóa kho, FEFO, ghi cách khách trả tiền); sau đó thời điểm phiếu được
đặt lại về ngày mô phỏng để báo cáo có chuỗi thời gian. Chỉ dùng cho dữ liệu mô phỏng.
"""

import math
from collections import Counter
from datetime import datetime, time, timedelta
from random import Random

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Min
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_vai_tro
from ung_dung.danh_muc.models import ChiNhanh, NhaCungCap, Thuoc
from ung_dung.kho.models import LoThuoc, PhieuNhap, TonKho
from ung_dung.kho.services.phieu_nhap import nhap_hang

from ..models import PhieuBan
from .phieu_ban import ban_tai_quay

TIEN_TO_LO = "LS-"
HE_SO_CHI_NHANH = (1.0, 0.8, 0.65)


def _thoi_diem(ngay, ngau_nhien):
    gio = time(ngau_nhien.randint(7, 20), ngau_nhien.randint(0, 59), ngau_nhien.randint(0, 59))
    return timezone.make_aware(datetime.combine(ngay, gio))


def _ke_hoach_ban(ngau_nhien, cac_thuoc, trong_so, ngay_dau, so_ngay, he_so):
    """Danh sách (ngày, các dòng): xu hướng tăng nhẹ, chu kỳ tháng, cuối tuần đông hơn."""
    ke_hoach = []
    for i in range(so_ngay):
        ngay = ngay_dau + timedelta(days=i)
        muc = (
            4.5
            * he_so
            * (1 + 0.25 * math.sin(2 * math.pi * i / 30))
            * (1.2 if ngay.weekday() >= 5 else 1)
            * (1 + 0.3 * i / so_ngay)
        )
        for _ in range(max(1, round(ngau_nhien.gauss(muc, 1.3)))):
            so_dong = min(ngau_nhien.choices((1, 2, 3), weights=(6, 3, 1))[0], len(cac_thuoc))
            chon = set()
            while len(chon) < so_dong:
                chon.add(ngau_nhien.choices(range(len(cac_thuoc)), weights=trong_so)[0])
            cac_dong = [
                {
                    "thuoc": cac_thuoc[j],
                    "so_luong": ngau_nhien.choices((1, 2, 3, 4), (5, 3, 2, 1))[0],
                }
                for j in sorted(chon)
            ]
            ke_hoach.append((ngay, cac_dong))
    return ke_hoach


def _nhap_lo_mo_phong(quan_ly, chi_nhanh, nha_cung_cap, cac_thuoc, han_hien_co, ke_hoach, ngay_dau):
    tong_theo_thuoc = Counter()
    for _, cac_dong in ke_hoach:
        for dong in cac_dong:
            tong_theo_thuoc[dong["thuoc"].pk] += dong["so_luong"]
    hom_nay = timezone.localdate()
    phieu_nhap = nhap_hang(
        quan_ly,
        chi_nhanh,
        nha_cung_cap,
        [
            {
                "thuoc": t,
                "ma_lo_thuoc": f"{TIEN_TO_LO}{chi_nhanh.pk}-{t.pk}",
                "ngay_het_han": (
                    han_hien_co[t.pk] - timedelta(days=1)
                    if t.pk in han_hien_co
                    else hom_nay + timedelta(days=180)
                ),
                "so_luong": tong_theo_thuoc[t.pk],
                "don_gia": t.gia_ban // 2,
            }
            for t in cac_thuoc
            if tong_theo_thuoc[t.pk]
        ],
        "Nhập hàng cho lịch sử bán mô phỏng",
    )
    PhieuNhap.objects.filter(pk=phieu_nhap.pk).update(
        thoi_diem_tao=timezone.make_aware(datetime.combine(ngay_dau - timedelta(days=1), time(8)))
    )


@transaction.atomic
def tao_lich_su_ban_mo_phong(nguoi, *, so_ngay=60, hat_giong=2026):
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
    if not 7 <= so_ngay <= 180:
        raise ValidationError("Số ngày mô phỏng từ 7 đến 180.")
    if LoThuoc.objects.filter(ma_lo_thuoc__startswith=TIEN_TO_LO).exists():
        raise ValidationError("Đã có lịch sử bán mô phỏng (lô LS-...), không tạo lần nữa.")
    nha_cung_cap = NhaCungCap.objects.filter(dang_hoat_dong=True).order_by("pk").first()
    if nha_cung_cap is None:
        raise ValidationError("Cần ít nhất một nhà cung cấp đang hoạt động.")
    ngau_nhien = Random(hat_giong)
    hom_nay = timezone.localdate()
    ngay_dau = hom_nay - timedelta(days=so_ngay)
    tat_ca_thuoc = list(
        Thuoc.objects.filter(dang_hoat_dong=True, la_thuoc_ke_don=False).order_by("ma_thuoc")
    )
    trong_so = {t.pk: ngau_nhien.uniform(0.3, 1.6) for t in tat_ca_thuoc}
    tai_khoan = get_user_model().objects.filter(dang_hoat_dong=True)
    tong_phieu = 0
    cac_chi_nhanh = ChiNhanh.objects.filter(dang_hoat_dong=True).order_by("pk")
    for thu_tu, chi_nhanh in enumerate(cac_chi_nhanh):
        quan_ly = tai_khoan.filter(chi_nhanh=chi_nhanh, vai_tro="quan_ly_chi_nhanh").first()
        nhan_vien = tai_khoan.filter(chi_nhanh=chi_nhanh, vai_tro="nhan_vien").first()
        if quan_ly is None or nhan_vien is None:
            continue
        # Hạn sớm nhất của lô còn hàng; lô mới phải hết hạn trước đó để FEFO chọn nó trước.
        han_hien_co = dict(
            TonKho.objects.filter(chi_nhanh=chi_nhanh, so_luong__gt=0)
            .values_list("lo_thuoc__thuoc")
            .annotate(han=Min("lo_thuoc__ngay_het_han"))
        )
        cac_thuoc = [
            t
            for t in tat_ca_thuoc
            if t.pk not in han_hien_co or han_hien_co[t.pk] > hom_nay + timedelta(days=2)
        ]
        if not cac_thuoc:
            continue
        ke_hoach = _ke_hoach_ban(
            ngau_nhien,
            cac_thuoc,
            [trong_so[t.pk] for t in cac_thuoc],
            ngay_dau,
            so_ngay,
            HE_SO_CHI_NHANH[thu_tu % len(HE_SO_CHI_NHANH)],
        )
        _nhap_lo_mo_phong(
            quan_ly, chi_nhanh, nha_cung_cap, cac_thuoc, han_hien_co, ke_hoach, ngay_dau
        )
        for ngay, cac_dong in ke_hoach:
            phieu = ban_tai_quay(
                nhan_vien,
                chi_nhanh,
                cac_dong,
                phuong_thuc_thanh_toan=ngau_nhien.choices(
                    ("tien_mat", "chuyen_khoan"), weights=(65, 35)
                )[0],
            )
            luc = _thoi_diem(ngay, ngau_nhien)
            PhieuBan.objects.filter(pk=phieu.pk).update(thoi_diem_tao=luc)
            tong_phieu += 1
    return f"Đã tạo {tong_phieu} phiếu bán mô phỏng trong {so_ngay} ngày, từ {ngay_dau:%d/%m/%Y}."
