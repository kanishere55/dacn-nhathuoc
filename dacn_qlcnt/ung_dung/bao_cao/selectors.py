from datetime import datetime, time, timedelta

from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone

from ung_dung.ban_hang.models import ChiTietPhieuBan, DonDatGiu, PhieuBan
from ung_dung.chung.permissions import kiem_tra_vai_tro
from ung_dung.danh_muc.selectors import lay_chi_nhanh
from ung_dung.kho.models import (
    ChiTietPhieuDieuChuyen,
    ChiTietPhieuKiemKe,
    ChiTietPhieuNhap,
    ChiTietPhieuTraNhaCungCap,
    PhieuDieuChuyen,
    PhieuKiemKe,
    PhieuNhap,
    PhieuTraNhaCungCap,
)
from ung_dung.kho.selectors import lay_ton_kha_dung


def lay_bao_cao(nguoi, tu_ngay, den_ngay, chi_nhanh=None):
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi", "quan_ly_chi_nhanh")
    tu_luc = timezone.make_aware(datetime.combine(tu_ngay, time.min))
    den_luc = timezone.make_aware(datetime.combine(den_ngay + timedelta(days=1), time.min))
    cac_chi_nhanh = lay_chi_nhanh(nguoi, ca_chi_nhanh_ngung=True)
    if chi_nhanh is not None:
        cac_chi_nhanh = cac_chi_nhanh.filter(pk=chi_nhanh.pk)
    trong_ky = {"thoi_diem_tao__gte": tu_luc, "thoi_diem_tao__lt": den_luc}

    phieu_nhap = PhieuNhap.objects.filter(chi_nhanh__in=cac_chi_nhanh, **trong_ky)
    phieu_ban = PhieuBan.objects.filter(chi_nhanh__in=cac_chi_nhanh, **trong_ky)
    phieu_tra = PhieuTraNhaCungCap.objects.filter(
        phieu_nhap__chi_nhanh__in=cac_chi_nhanh, **trong_ky
    )
    phieu_kiem_ke = PhieuKiemKe.objects.filter(chi_nhanh__in=cac_chi_nhanh, **trong_ky)
    chuyen_di = PhieuDieuChuyen.objects.filter(chi_nhanh_nguon__in=cac_chi_nhanh, **trong_ky)
    chuyen_den = PhieuDieuChuyen.objects.filter(chi_nhanh_dich__in=cac_chi_nhanh, **trong_ky)
    phieu_chuyen = PhieuDieuChuyen.objects.filter(
        Q(chi_nhanh_nguon__in=cac_chi_nhanh) | Q(chi_nhanh_dich__in=cac_chi_nhanh), **trong_ky
    )
    don = DonDatGiu.objects.filter(chi_nhanh__in=cac_chi_nhanh, **trong_ky)
    dong_ban = ChiTietPhieuBan.objects.filter(phieu_ban__in=phieu_ban)
    tien = ExpressionWrapper(F("so_luong") * F("don_gia"), output_field=DecimalField())
    cac_luong = {}
    cac_nhom = [
        (
            "nhap",
            ChiTietPhieuNhap.objects.filter(phieu_nhap__in=phieu_nhap),
            "lo_thuoc__thuoc",
            "so_luong",
        ),
        ("ban", dong_ban, "thuoc", "so_luong"),
        (
            "tra",
            ChiTietPhieuTraNhaCungCap.objects.filter(phieu_tra_nha_cung_cap__in=phieu_tra),
            "lo_thuoc__thuoc",
            "so_luong",
        ),
        (
            "chuyen_di",
            ChiTietPhieuDieuChuyen.objects.filter(phieu_dieu_chuyen__in=chuyen_di),
            "lo_thuoc__thuoc",
            "so_luong",
        ),
        (
            "chuyen_den",
            ChiTietPhieuDieuChuyen.objects.filter(phieu_dieu_chuyen__in=chuyen_den),
            "lo_thuoc__thuoc",
            "so_luong",
        ),
        (
            "dieu_chinh",
            ChiTietPhieuKiemKe.objects.filter(phieu_kiem_ke__in=phieu_kiem_ke),
            "lo_thuoc__thuoc",
            F("so_luong_thuc_te") - F("so_luong_so_sach"),
        ),
        (
            "kha_dung",
            lay_ton_kha_dung().filter(chi_nhanh__in=cac_chi_nhanh),
            "lo_thuoc__thuoc",
            "kha_dung",
        ),
    ]
    for ten, tap, duong_dan, bieu_thuc in cac_nhom:
        cot = f"{duong_dan}__don_vi_tinh__ma_don_vi_tinh"
        for dong in tap.order_by().values(cot).annotate(tong=Sum(bieu_thuc)):
            cac_luong.setdefault(dong[cot], {})[ten] = dong["tong"]
    return {
        "so_phieu_nhap": phieu_nhap.count(),
        "so_phieu_ban": phieu_ban.count(),
        "so_phieu_tra": phieu_tra.count(),
        "so_phieu_kiem_ke": phieu_kiem_ke.count(),
        "so_phieu_chuyen": phieu_chuyen.count(),
        "so_don_giu": don.count(),
        "tong_tien_ban": dong_ban.aggregate(tong=Sum(tien, default=0))["tong"],
        "cac_luong": sorted(cac_luong.items()),
    }
