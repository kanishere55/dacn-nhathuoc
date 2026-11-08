from django.test import TestCase
from django.urls import reverse

from ung_dung.kho.tests.du_lieu import tao_du_lieu


class HaiKhuTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_cac_ten_url_noi_bo_tro_toi_quan_ly_va_chan_khach(self):
        self.client.force_login(self.d.khach)
        for ten in (
            "chung:bang_dieu_khien",
            "tai_khoan:danh_sach",
            "danh_muc:thuoc_danh_sach",
            "kho:ton_kho_danh_sach",
            "ban_hang:phieu_ban_danh_sach",
            "ban_hang:don_dat_giu_danh_sach",
            "tro_chuyen:danh_sach",
            "bao_cao:tong_hop",
            "webgis:ban_do_nhiet",
            "webgis:du_lieu_nhiet",
            "du_bao:ket_qua",
        ):
            with self.subTest(ten=ten):
                url = reverse(ten)
                self.assertTrue(url.startswith("/quan-ly/"))
                self.assertEqual(self.client.get(url).status_code, 403)
        self.assertContains(self.client.get(reverse("tai_khoan:cua_toi")), "Đơn đặt giữ của tôi")

    def test_dang_nhap_nhan_su_den_khu_quan_ly_va_xem_duoc_website_khach(self):
        for nguoi in (self.d.admin, self.d.ql, self.d.nv):
            with self.subTest(vai_tro=nguoi.vai_tro):
                self.client.logout()
                phan_hoi = self.client.post(
                    reverse("tai_khoan:dang_nhap"),
                    {"username": nguoi.ten_dang_nhap, "password": "Mat-khau-thu-2026!"},
                )
                self.assertRedirects(phan_hoi, reverse("chung:bang_dieu_khien"))
                self.assertContains(self.client.get("/"), "Khu quản lý")
                self.assertEqual(self.client.get(reverse("tai_khoan:cua_toi")).status_code, 403)

    def test_khach_vang_lai_dang_nhap_quay_lai_trang_tro_chuyen(self):
        url = reverse("tro_chuyen:khach_danh_sach")
        chuyen_huong = self.client.get(url)
        self.assertEqual(chuyen_huong.status_code, 302)
        self.assertContains(self.client.get(chuyen_huong.url), 'name="next"')
        phan_hoi = self.client.post(
            chuyen_huong.url,
            {"username": self.d.khach.ten_dang_nhap, "password": "Mat-khau-thu-2026!"},
        )
        self.assertRedirects(phan_hoi, url)
        self.client.logout()
        phan_hoi = self.client.post(
            reverse("tai_khoan:dang_nhap"),
            {
                "username": self.d.khach.ten_dang_nhap,
                "password": "Mat-khau-thu-2026!",
                "next": "https://vi-du.invalid/",
            },
        )
        self.assertRedirects(phan_hoi, "/")

    def test_khach_mo_phong_tu_chi_tiet_chi_nhanh(self):
        chi_nhanh = self.d.cn
        self.client.force_login(self.d.khach)
        trang = self.client.get(
            reverse("danh_muc:khach_chi_nhanh_chi_tiet", args=[chi_nhanh.ma_chi_nhanh])
        )
        url = reverse("tro_chuyen:khach_danh_sach")
        self.assertContains(trang, f"{url}?chi_nhanh={chi_nhanh.ma_chi_nhanh}")
        self.assertEqual(
            self.client.get(url, {"chi_nhanh": chi_nhanh.ma_chi_nhanh})
            .context["form"]
            .initial["chi_nhanh"],
            chi_nhanh,
        )
        phan_hoi = self.client.post(url, {"chi_nhanh": chi_nhanh.pk}, follow=True)
        self.assertContains(phan_hoi, "Tin nhắn")
        self.assertNotContains(phan_hoi, "KHU QUẢN LÝ")
