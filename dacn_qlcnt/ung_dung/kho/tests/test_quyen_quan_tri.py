from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import PhieuDieuChuyen, PhieuKiemKe, PhieuNhap, PhieuTraNhaCungCap, TonKho
from ..services.phieu_dieu_chuyen import dieu_chuyen
from ..services.phieu_kiem_ke import kiem_ke
from ..services.phieu_nhap import nhap_hang
from ..services.phieu_tra_nha_cung_cap import tra_nha_cung_cap
from .du_lieu import tao_du_lieu


class QuyenQuanTriKhoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        cls.dong_nhap = {
            "thuoc": cls.d.thuoc,
            "ma_lo_thuoc": "LO-NHAP",
            "ngay_het_han": timezone.localdate() + timedelta(days=10),
            "so_luong": 20,
            "don_gia": 1000,
        }
        cls.phieu = nhap_hang(cls.d.ql2, cls.d.cn2, cls.d.ncc, [cls.dong_nhap])
        cls.ton = TonKho.objects.get(chi_nhanh=cls.d.cn2)

    def setUp(self):
        self.client.force_login(self.d.admin)

    def kiem_tra_chan_ghi(self, ten_phieu, service, *tham_so):
        with self.assertRaises(PermissionDenied):
            service(self.d.admin, *tham_so)
        url = reverse(f"kho:{ten_phieu}_tao")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertEqual(TonKho.objects.get(pk=self.ton.pk).so_luong, 20)

    def test_quan_tri_khong_lap_phieu_nhap(self):
        d = self.d
        self.kiem_tra_chan_ghi("phieu_nhap", nhap_hang, d.cn2, d.ncc, [self.dong_nhap])
        self.assertEqual(PhieuNhap.objects.count(), 1)

    def test_quan_tri_khong_dieu_chuyen(self):
        d = self.d
        self.kiem_tra_chan_ghi(
            "phieu_dieu_chuyen", dieu_chuyen, d.cn2, d.cn, [{"thuoc": d.thuoc, "so_luong": 3}]
        )
        self.assertFalse(PhieuDieuChuyen.objects.exists())
        self.assertFalse(TonKho.objects.filter(chi_nhanh=d.cn).exists())

    def test_quan_tri_khong_tra_nha_cung_cap(self):
        self.kiem_tra_chan_ghi(
            "phieu_tra",
            tra_nha_cung_cap,
            self.phieu,
            [{"lo_thuoc": self.ton.lo_thuoc, "so_luong": 2}],
        )
        self.assertFalse(PhieuTraNhaCungCap.objects.exists())

    def test_quan_tri_khong_kiem_ke(self):
        self.kiem_tra_chan_ghi(
            "phieu_kiem_ke",
            kiem_ke,
            self.d.cn2,
            [{"ton_kho": self.ton, "so_luong_so_sach": 20, "so_luong_thuc_te": 18}],
        )
        self.assertFalse(PhieuKiemKe.objects.exists())

    def test_quan_tri_xem_ton_va_chung_tu_nhung_khong_co_nut_tao(self):
        d = self.d
        phieu_tra = tra_nha_cung_cap(
            d.ql2, self.phieu, [{"lo_thuoc": self.ton.lo_thuoc, "so_luong": 2}]
        )
        phieu_chuyen = dieu_chuyen(d.ql2, d.cn2, d.cn, [{"thuoc": d.thuoc, "so_luong": 3}])
        phieu_kiem = kiem_ke(
            d.ql2,
            d.cn2,
            [{"ton_kho": self.ton, "so_luong_so_sach": 15, "so_luong_thuc_te": 14}],
        )
        for ten, phieu in (
            ("phieu_nhap", self.phieu),
            ("phieu_tra", phieu_tra),
            ("phieu_dieu_chuyen", phieu_chuyen),
            ("phieu_kiem_ke", phieu_kiem),
        ):
            with self.subTest(chung_tu=ten):
                trang = self.client.get(reverse(f"kho:{ten}_danh_sach"))
                self.assertContains(trang, str(phieu))
                self.assertNotContains(trang, reverse(f"kho:{ten}_tao"))
                chi_tiet = self.client.get(reverse(f"kho:{ten}_chi_tiet", args=[phieu.pk]))
                self.assertContains(chi_tiet, str(phieu))
        ton = self.client.get(reverse("kho:ton_kho_danh_sach"))
        self.assertContains(ton, d.cn.ten_chi_nhanh)
        self.assertContains(ton, d.cn2.ten_chi_nhanh)
        self.client.force_login(d.ql2)
        self.assertContains(self.client.get(reverse("kho:phieu_kiem_ke_danh_sach")), "Lập phiếu mới")

    def test_quan_tri_van_doi_duoc_trang_thai_lo(self):
        lo = self.ton.lo_thuoc
        url = reverse("kho:lo_thuoc_doi_trang_thai", args=[lo.pk])
        self.assertContains(self.client.get(reverse("kho:lo_thuoc_danh_sach")), url)
        self.assertEqual(self.client.post(url, {"duoc_phep_ban": "0"}).status_code, 302)
        lo.refresh_from_db()
        self.assertFalse(lo.duoc_phep_ban)
