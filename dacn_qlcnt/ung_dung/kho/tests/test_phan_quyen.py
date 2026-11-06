from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ung_dung.kho.models import PhieuNhap
from ung_dung.kho.selectors import lay_canh_bao_ton_thap
from ung_dung.kho.services.phieu_nhap import nhap_hang

from .du_lieu import tao_du_lieu, tao_ton


class PhamViChiNhanhTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_nhan_vien_chi_thay_chung_tu_va_ton_chi_nhanh_cua_minh(self):
        d = self.d
        dong = {
            "thuoc": d.thuoc,
            "so_luong": 10,
            "ma_lo_thuoc": "LO-CHUNG",
            "ngay_het_han": timezone.localdate(),
            "don_gia": 1000,
        }
        cua_minh = nhap_hang(d.nv, d.cn, d.ncc, [dong])
        cua_khac = nhap_hang(d.admin, d.cn2, d.ncc, [dong])
        self.client.force_login(d.nv)
        trang = self.client.get(reverse("kho:phieu_nhap_danh_sach"))
        self.assertContains(trang, cua_minh.ma_phieu_nhap)
        self.assertNotContains(trang, cua_khac.ma_phieu_nhap)
        self.assertEqual(
            self.client.get(reverse("kho:phieu_nhap_chi_tiet", args=[cua_khac.pk])).status_code, 404
        )
        trang = self.client.get(reverse("kho:ton_kho_danh_sach"))
        self.assertContains(trang, d.cn.ten_chi_nhanh)
        self.assertNotContains(trang, d.cn2.ten_chi_nhanh)

    def test_nhan_vien_khong_ghi_duoc_khi_gia_chi_nhanh_trong_post(self):
        self.client.force_login(self.d.nv)
        du_lieu = {
            "chi_nhanh": self.d.cn2.pk,
            "nha_cung_cap": self.d.ncc.pk,
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-0-thuoc": self.d.thuoc.pk,
            "form-0-so_luong": "3",
            "form-0-ma_lo_thuoc": "LO-GIA-MAO",
            "form-0-ngay_het_han": timezone.localdate().isoformat(),
            "form-0-don_gia": "1000",
        }
        phan_hoi = self.client.post(reverse("kho:phieu_nhap_tao"), du_lieu)
        self.assertEqual(phan_hoi.status_code, 200)
        self.assertFalse(PhieuNhap.objects.exists())
        du_lieu["chi_nhanh"] = self.d.cn.pk
        self.assertEqual(self.client.post(reverse("kho:phieu_nhap_tao"), du_lieu).status_code, 302)
        self.assertEqual(PhieuNhap.objects.get().chi_nhanh, self.d.cn)

    def test_canh_bao_cong_cac_lo_va_bao_ca_thuoc_khong_co_ton(self):
        d = self.d
        d.thuoc.nguong_canh_bao = 10
        d.thuoc.save(update_fields=["nguong_canh_bao"])
        self.assertEqual(lay_canh_bao_ton_thap(d.nv)[0][1].kha_dung, 0)
        tao_ton(d, "LO1", luong=6)
        tao_ton(d, "LO2", luong=5)
        tao_ton(d, "LO3", luong=100, ngay=-1, chi_nhanh=d.cn2)
        self.assertEqual(lay_canh_bao_ton_thap(d.nv), [])
        self.assertEqual(
            [(cn.pk, thuoc.kha_dung) for cn, thuoc in lay_canh_bao_ton_thap(d.admin)],
            [(d.cn2.pk, 0)],
        )
