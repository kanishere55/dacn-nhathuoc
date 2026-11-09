from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from ung_dung.ban_hang.services.dat_hang import dat_giu
from ung_dung.kho.models import ChiTietPhieuXuatHuy, PhieuXuatHuy
from ung_dung.kho.services.phieu_nhap import nhap_hang
from ung_dung.kho.services.phieu_xuat_huy import xuat_huy

from .du_lieu import tao_du_lieu, tao_ton


class XuatHuyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_het_han_chi_nhan_lo_qua_han_va_tru_ton(self):
        d = self.d
        qua_han = tao_ton(d, "LO-CU", ngay=-1, luong=7)
        con_han = tao_ton(d, "LO-MOI", ngay=0, luong=5)
        with self.assertRaises(ValidationError):
            xuat_huy(d.ql, d.cn, "het_han", [{"lo_thuoc": con_han.lo_thuoc, "so_luong": 1}])
        phieu = xuat_huy(d.ql, d.cn, "het_han", [{"lo_thuoc": qua_han.lo_thuoc, "so_luong": 7}])
        qua_han.refresh_from_db()
        self.assertEqual(qua_han.so_luong, 0)
        self.assertEqual(ChiTietPhieuXuatHuy.objects.get(phieu_xuat_huy=phieu).so_luong, 7)

    def test_hu_hong_can_ghi_chu_va_khong_cham_phan_dang_giu(self):
        d = self.d
        ton = tao_ton(d, "LO-HONG", ngay=30, luong=10)
        dat_giu(d.khach, d.cn, [{"thuoc": d.thuoc, "so_luong": 6}])
        dong = [{"lo_thuoc": ton.lo_thuoc, "so_luong": 5}]
        with self.assertRaises(ValidationError):
            xuat_huy(d.ql, d.cn, "hu_hong", dong, "")
        with self.assertRaises(ValidationError):
            xuat_huy(d.ql, d.cn, "hu_hong", dong, "Vỡ hộp khi xếp kệ")
        self.assertFalse(PhieuXuatHuy.objects.exists())
        dong[0]["so_luong"] = 4
        xuat_huy(d.ql, d.cn, "hu_hong", dong, "Vỡ hộp khi xếp kệ")
        ton.refresh_from_db()
        self.assertEqual(ton.so_luong, 6)

    def test_chi_quan_ly_dung_chi_nhanh_duoc_huy(self):
        d = self.d
        ton = tao_ton(d, "LO-QH", ngay=-3, luong=2)
        dong = [{"lo_thuoc": ton.lo_thuoc, "so_luong": 1}]
        for nguoi in (d.nv, d.ql2, d.admin):
            with self.assertRaises(PermissionDenied):
                xuat_huy(nguoi, d.cn, "het_han", dong)

    def test_lap_san_lo_het_han_va_xac_nhan_qua_web(self):
        d = self.d
        ton = tao_ton(d, "LO-WEB", ngay=-2, luong=3)
        self.client.force_login(d.ql)
        trang = self.client.get(reverse("kho:phieu_xuat_huy_tao") + "?loai=het_han")
        self.assertContains(trang, "LO-WEB")
        phan_hoi = self.client.post(
            reverse("kho:phieu_xuat_huy_tao"),
            {
                "chi_nhanh": d.cn.pk,
                "loai_xuat_huy": "het_han",
                "ghi_chu": "",
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-0-lo_thuoc": ton.lo_thuoc.pk,
                "form-0-so_luong": "3",
            },
        )
        phieu = PhieuXuatHuy.objects.get()
        self.assertRedirects(phan_hoi, reverse("kho:phieu_xuat_huy_chi_tiet", args=[phieu.pk]))


class ChungTuPdfTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from datetime import timedelta

        from django.utils import timezone

        cls.d = tao_du_lieu()
        cls.phieu = nhap_hang(
            cls.d.nv,
            cls.d.cn,
            cls.d.ncc,
            [
                {
                    "thuoc": cls.d.thuoc,
                    "so_luong": 4,
                    "ma_lo_thuoc": "LO-PDF",
                    "ngay_het_han": timezone.localdate() + timedelta(days=90),
                    "don_gia": 1500,
                }
            ],
        )

    def test_chi_tiet_va_pdf_phieu_nhap(self):
        self.client.force_login(self.d.ql)
        chi_tiet = self.client.get(reverse("kho:phieu_nhap_chi_tiet", args=[self.phieu.pk]))
        self.assertContains(chi_tiet, "LO-PDF")
        self.assertContains(chi_tiet, "6.000 đ")
        pdf = self.client.get(reverse("kho:phieu_nhap_pdf", args=[self.phieu.pk]) + "?tai=1")
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertIn("attachment", pdf["Content-Disposition"])

    def test_pdf_chi_nhanh_khac_bi_chan(self):
        self.client.force_login(self.d.ql2)
        phan_hoi = self.client.get(reverse("kho:phieu_nhap_pdf", args=[self.phieu.pk]))
        self.assertEqual(phan_hoi.status_code, 404)
