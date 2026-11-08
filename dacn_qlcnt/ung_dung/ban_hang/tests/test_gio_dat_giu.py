from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.conf import settings
from django.contrib.sessions.models import Session
from django.db import close_old_connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from ung_dung.kho.selectors import lay_ton_kha_dung
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton

from ..gio_dat_giu import KHOA_GIO
from ..models import DonDatGiu
from ..services.dat_giu import dat_giu


class GioDatGiuTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        cls.ton = tao_ton(cls.d, luong=10)
        tao_ton(cls.d, ma="LO-CN2", luong=2, chi_nhanh=cls.d.cn2)

    def setUp(self):
        self.url_gio = reverse("ban_hang:gio_dat_giu")
        self.url_them = reverse("ban_hang:gio_dat_giu_them", args=[self.d.thuoc.ma_thuoc])
        self.url_sua = reverse("ban_hang:gio_dat_giu_sua", args=[self.d.thuoc.pk])
        self.url_xac_nhan = reverse("ban_hang:gio_dat_giu_xac_nhan")

    def test_khach_vang_lai_them_sua_bo_va_luu_gio_trong_phien_postgresql(self):
        self.assertContains(self.client.get(self.url_gio), "Giỏ của bạn đang trống")
        self.assertRedirects(self.client.post(self.url_them, {"so_luong": 2}), self.url_gio)
        self.client.post(self.url_them, {"so_luong": 1})
        trang = self.client.get(self.url_gio)
        self.assertContains(trang, 'value="3"')
        self.assertContains(trang, "Đăng nhập để đặt giữ")
        self.assertEqual(lay_ton_kha_dung().get(pk=self.ton.pk).kha_dung, 10)
        self.client.post(self.url_sua, {"so_luong": 4})
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        phien = Session.objects.get(session_key=cookie).get_decoded()
        self.assertEqual(phien[KHOA_GIO], {str(self.d.thuoc.pk): 4})
        self.client.post(self.url_sua, {"so_luong": 0})
        self.assertContains(self.client.get(self.url_gio), "Giỏ của bạn đang trống")
        self.assertFalse(DonDatGiu.objects.exists())

    def test_dang_nhap_giu_gio_va_chon_duoc_chi_nhanh_con_du(self):
        d = self.d
        self.client.post(self.url_them, {"so_luong": 3})
        bat_dang_nhap = self.client.post(self.url_xac_nhan, {"chi_nhanh": d.cn.pk})
        self.assertEqual(bat_dang_nhap.status_code, 302)
        self.assertIn("next=/gio-dat-giu/", bat_dang_nhap.url)
        self.assertFalse(DonDatGiu.objects.exists())
        phan_hoi = self.client.post(
            bat_dang_nhap.url,
            {"username": d.khach.ten_dang_nhap, "password": "Mat-khau-thu-2026!"},
        )
        self.assertRedirects(phan_hoi, self.url_gio)
        trang = self.client.get(self.url_gio, {"chi_nhanh": d.cn.ma_chi_nhanh})
        self.assertEqual(list(trang.context["form"].fields["chi_nhanh"].queryset), [d.cn])
        self.assertEqual(trang.context["form"].initial["chi_nhanh"], d.cn.pk)
        self.assertContains(trang, 'value="3"')
        self.assertContains(trang, "Xác nhận đặt giữ")
        ket_qua = self.client.post(self.url_xac_nhan, {"chi_nhanh": d.cn.pk})
        don = DonDatGiu.objects.get(khach_hang=d.khach)
        url_don = reverse("ban_hang:khach_don_dat_giu_chi_tiet", args=[don.pk])
        self.assertRedirects(ket_qua, url_don)
        self.assertEqual(lay_ton_kha_dung().get(pk=self.ton.pk).kha_dung, 7)
        self.assertNotIn(KHOA_GIO, self.client.session)
        self.client.post(self.url_xac_nhan, {"chi_nhanh": d.cn.pk})
        self.assertEqual(DonDatGiu.objects.count(), 1)

        self.client.force_login(d.khac)
        self.assertNotContains(
            self.client.get(reverse("ban_hang:khach_don_dat_giu_danh_sach")), don.ma_don_dat_giu
        )
        self.assertEqual(self.client.get(url_don).status_code, 404)
        url_huy = reverse("ban_hang:khach_don_dat_giu_huy", args=[don.pk])
        self.assertEqual(self.client.post(url_huy).status_code, 404)
        self.client.force_login(d.khach)
        self.assertContains(
            self.client.get(reverse("ban_hang:khach_don_dat_giu_danh_sach")), don.ma_don_dat_giu
        )
        self.assertRedirects(self.client.post(url_huy), url_don)
        don.refresh_from_db()
        self.assertEqual(don.trang_thai, "da_huy")
        self.assertEqual(lay_ton_kha_dung().get(pk=self.ton.pk).kha_dung, 10)

    def test_khong_du_hang_luc_xac_nhan_thi_giu_nguyen_gio(self):
        d = self.d
        self.client.force_login(d.khach)
        self.client.post(self.url_them, {"so_luong": 3})
        self.assertContains(self.client.get(self.url_gio), "Xác nhận đặt giữ")
        dat_giu(d.khac, d.cn, [{"thuoc": d.thuoc, "so_luong": 8}])
        for chi_nhanh in (d.cn, d.cn2):
            with self.subTest(chi_nhanh=chi_nhanh):
                phan_hoi = self.client.post(
                    self.url_xac_nhan, {"chi_nhanh": chi_nhanh.pk}, follow=True
                )
                self.assertContains(phan_hoi, "Không đủ tồn khả dụng")
                self.assertEqual(self.client.session[KHOA_GIO], {str(d.thuoc.pk): 3})
        self.assertFalse(DonDatGiu.objects.filter(khach_hang=d.khach).exists())

    def test_thuoc_ngung_kinh_doanh_co_the_bo_khoi_gio(self):
        self.client.force_login(self.d.khach)
        self.client.post(self.url_them, {"so_luong": 1})
        thuoc = self.d.thuoc
        thuoc.dang_hoat_dong = False
        thuoc.save(update_fields=["dang_hoat_dong"])
        self.assertContains(self.client.get(self.url_gio), "Vui lòng bỏ thuốc này")
        phan_hoi = self.client.post(self.url_xac_nhan, {"chi_nhanh": self.d.cn.pk}, follow=True)
        self.assertContains(phan_hoi, "Vui lòng bỏ thuốc đã ngừng")
        self.assertFalse(DonDatGiu.objects.exists())
        self.client.post(self.url_sua, {"so_luong": 0})
        self.assertContains(self.client.get(self.url_gio), "Giỏ của bạn đang trống")
        self.assertEqual(self.client.post(self.url_them, {"so_luong": 1}).status_code, 404)

    def test_nhan_su_khong_thao_tac_gio_cua_khach(self):
        for nguoi in (self.d.admin, self.d.ql, self.d.nv):
            with self.subTest(vai_tro=nguoi.vai_tro):
                self.client.force_login(nguoi)
                self.assertEqual(self.client.get(self.url_gio).status_code, 403)
                self.assertEqual(self.client.post(self.url_them, {"so_luong": 1}).status_code, 403)
                self.assertEqual(self.client.post(self.url_sua, {"so_luong": 1}).status_code, 403)
                self.assertEqual(
                    self.client.post(self.url_xac_nhan, {"chi_nhanh": self.d.cn.pk}).status_code,
                    403,
                )


class XacNhanGioDongThoiTests(TransactionTestCase):
    def test_hai_luot_xac_nhan_cung_gio_chi_tao_mot_don(self):
        d = tao_du_lieu()
        tao_ton(d, luong=10)
        self.client.force_login(d.khach)
        self.client.post(
            reverse("ban_hang:gio_dat_giu_them", args=[d.thuoc.ma_thuoc]), {"so_luong": 2}
        )
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        url = reverse("ban_hang:gio_dat_giu_xac_nhan")
        bat_dau = Barrier(2)

        def xac_nhan():
            try:
                client = Client()
                client.cookies[settings.SESSION_COOKIE_NAME] = cookie
                bat_dau.wait(timeout=5)
                return client.post(url, {"chi_nhanh": d.cn.pk}).url
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as nhom:
            tac_vu = [nhom.submit(xac_nhan) for _ in range(2)]
            duong_dan = [t.result(timeout=15) for t in tac_vu]
        don = DonDatGiu.objects.get()
        self.assertCountEqual(
            duong_dan,
            [
                reverse("ban_hang:gio_dat_giu"),
                reverse("ban_hang:khach_don_dat_giu_chi_tiet", args=[don.pk]),
            ],
        )
