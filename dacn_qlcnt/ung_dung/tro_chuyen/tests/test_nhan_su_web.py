"""Nhân sự nhà thuốc xem website khách: không bị dẫn tới trang chỉ dành cho khách."""

from django.test import TestCase
from django.urls import reverse

from ung_dung.kho.tests.du_lieu import tao_du_lieu


class NhanSuXemWebsiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_nhan_su_bam_hoi_duoc_si_ve_trang_tro_chuyen_noi_bo(self):
        self.client.force_login(self.d.nv)
        phan_hoi = self.client.get(reverse("tro_chuyen:khach_danh_sach"))
        self.assertRedirects(
            phan_hoi, reverse("tro_chuyen:danh_sach"), fetch_redirect_response=False
        )

    def test_ban_do_khong_co_nut_dat_hang_cho_nhan_su(self):
        self.client.force_login(self.d.nv)
        self.assertNotContains(self.client.get(reverse("webgis:ban_do")), "data-url-dat-hang")
        self.client.force_login(self.d.khach)
        self.assertContains(self.client.get(reverse("webgis:ban_do")), "data-url-dat-hang")
