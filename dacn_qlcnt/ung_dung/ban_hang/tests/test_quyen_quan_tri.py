from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from ung_dung.kho.models import TonKho
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton

from ..models import DonHang, PhieuBan
from ..services.dat_hang import dat_giu
from ..services.don_hang import huy_don
from ..services.phieu_ban import ban_tai_quay


class QuyenQuanTriBanHangTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        cls.quan_tri = get_user_model().objects.create_user(
            "quan_tri_chuoi_thu", vai_tro="quan_tri_chuoi"
        )
        cls.ton = tao_ton(cls.d, "LO-CN2", chi_nhanh=cls.d.cn2, luong=20)
        cls.dong = [{"thuoc": cls.d.thuoc, "so_luong": 2}]
        cls.don = dat_giu(cls.d.khach, cls.d.cn2, cls.dong)

    def setUp(self):
        self.client.force_login(self.quan_tri)

    def test_quan_tri_khong_lap_phieu_ban_tai_quay(self):
        with self.assertRaises(PermissionDenied):
            ban_tai_quay(self.quan_tri, self.d.cn2, self.dong)
        url = reverse("ban_hang:phieu_ban_tao")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertFalse(PhieuBan.objects.exists())
        self.assertEqual(TonKho.objects.get(pk=self.ton.pk).so_luong, 20)

    def test_quan_tri_khong_dat_giu(self):
        with self.assertRaises(PermissionDenied):
            dat_giu(self.quan_tri, self.d.cn2, self.dong)
        self.assertEqual(
            self.client.post(
                reverse("webgis:dat_giu"),
                {
                    "id_chi_nhanh": self.d.cn2.pk,
                    "cac_thuoc": [{"id_thuoc": self.d.thuoc.pk, "so_luong": 2}],
                },
                content_type="application/json",
            ).status_code,
            403,
        )
        self.assertNotContains(self.client.get(reverse("webgis:ban_do")), "data-url-giu=")
        self.assertEqual(DonHang.objects.count(), 1)

    def test_quan_tri_khong_nhan_don_giu(self):
        with self.assertRaises(PermissionDenied):
            ban_tai_quay(self.quan_tri, self.d.cn2, [], don_hang=self.don)
        self.assertEqual(
            self.client.post(
                reverse("ban_hang:don_hang_xu_ly", args=[self.don.pk, "nhan_tai_quay"])
            ).status_code,
            403,
        )
        self.assertFalse(PhieuBan.objects.exists())
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "dang_giu")

    def test_quan_tri_khong_huy_don_giu(self):
        with self.assertRaises(PermissionDenied):
            huy_don(self.quan_tri, self.don)
        self.assertEqual(
            self.client.post(
                reverse("ban_hang:don_hang_xu_ly", args=[self.don.pk, "huy"])
            ).status_code,
            403,
        )
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "dang_giu")

    def test_quan_tri_xem_phieu_ban_va_don_giu_khong_co_nut_ghi(self):
        d = self.d
        tao_ton(d)
        don_cn1 = dat_giu(d.khach, d.cn, self.dong)
        phieu_cn1 = ban_tai_quay(d.nv, d.cn, self.dong)
        phieu_cn2 = ban_tai_quay(d.ql2, d.cn2, self.dong)
        trang = self.client.get(reverse("ban_hang:phieu_ban_danh_sach"))
        self.assertNotContains(trang, reverse("ban_hang:phieu_ban_tao"))
        for phieu in (phieu_cn1, phieu_cn2):
            self.assertContains(trang, str(phieu))
            self.assertContains(
                self.client.get(reverse("ban_hang:phieu_ban_chi_tiet", args=[phieu.pk])),
                str(phieu),
            )
        trang = self.client.get(reverse("ban_hang:don_hang_danh_sach"))
        for don in (don_cn1, self.don):
            self.assertContains(trang, str(don))
            chi_tiet = self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[don.pk]))
            self.assertContains(chi_tiet, str(don))
            self.assertNotContains(
                chi_tiet, reverse("ban_hang:don_hang_xu_ly", args=[don.pk, "nhan_tai_quay"])
            )
            self.assertNotContains(
                chi_tiet, reverse("ban_hang:don_hang_xu_ly", args=[don.pk, "huy"])
            )
        self.client.force_login(d.ql2)
        chi_tiet = self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[self.don.pk]))
        self.assertContains(chi_tiet, "Hủy đơn")
        self.assertContains(chi_tiet, "Khách đã nhận và thanh toán tại quầy")
