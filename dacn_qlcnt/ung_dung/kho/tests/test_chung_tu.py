from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from ung_dung.danh_muc.models import QuyDoiBaoGoi
from ung_dung.kho.models import PhieuKiemKe, PhieuTraNhaCungCap, TonKho
from ung_dung.kho.services.phieu_dieu_chuyen import dieu_chuyen
from ung_dung.kho.services.phieu_kiem_ke import kiem_ke
from ung_dung.kho.services.phieu_nhap import nhap_hang
from ung_dung.kho.services.phieu_tra_nha_cung_cap import tra_nha_cung_cap

from .du_lieu import tao_du_lieu


class ChungTuKhoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def nhap_lo(self, luong, quy_doi=None):
        d = self.d
        return nhap_hang(
            d.nv,
            d.cn,
            d.ncc,
            [
                {
                    "thuoc": d.thuoc,
                    "so_luong": luong,
                    "quy_doi_bao_goi": quy_doi,
                    "ma_lo_thuoc": "LO-10",
                    "ngay_het_han": timezone.localdate() + timedelta(days=10),
                    "don_gia": 1000,
                }
            ],
        )

    def test_nhap_quy_doi_va_tra_ncc_khong_chiem_phan_dang_giu(self):
        d = self.d
        quy_doi = QuyDoiBaoGoi.objects.create(thuoc=d.thuoc, ten_quy_doi_bao_goi="Hộp", he_so=10)
        phieu = self.nhap_lo(2, quy_doi)
        ton = TonKho.objects.get(chi_nhanh=d.cn)
        self.assertEqual(ton.so_luong, 20)
        from ung_dung.ban_hang.services.dat_giu import dat_giu

        dat_giu(d.khach, d.cn, [{"thuoc": d.thuoc, "so_luong": 12}])
        dong = {"lo_thuoc": ton.lo_thuoc, "so_luong": 9}
        with self.assertRaises(ValidationError):
            tra_nha_cung_cap(d.ql, phieu, [dong])
        self.assertFalse(PhieuTraNhaCungCap.objects.exists())
        dong["so_luong"] = 8
        tra_nha_cung_cap(d.ql, phieu, [dong])
        ton.refresh_from_db()
        self.assertEqual(ton.so_luong, 12)

    def test_dieu_chuyen_giu_nguyen_tong_va_kiem_ke_tu_choi_so_du_cu(self):
        d = self.d
        self.nhap_lo(20)
        ton = TonKho.objects.get(chi_nhanh=d.cn)
        dieu_chuyen(d.ql, d.cn, d.cn2, [{"thuoc": d.thuoc, "so_luong": 7}])
        ton.refresh_from_db()
        self.assertEqual(ton.so_luong, 13)
        self.assertEqual(TonKho.objects.get(chi_nhanh=d.cn2, lo_thuoc=ton.lo_thuoc).so_luong, 7)
        dong = {"ton_kho": ton, "so_luong_so_sach": 20, "so_luong_thuc_te": 13}
        with self.assertRaises(ValidationError):
            kiem_ke(d.ql, d.cn, [dong])
        self.assertFalse(PhieuKiemKe.objects.exists())
        dong["so_luong_so_sach"] = 13
        dong["so_luong_thuc_te"] = 12
        kiem_ke(d.ql, d.cn, [dong])
        ton.refresh_from_db()
        self.assertEqual(ton.so_luong, 12)
