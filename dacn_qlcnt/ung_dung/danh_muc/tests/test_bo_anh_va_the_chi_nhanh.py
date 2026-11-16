"""Bộ ảnh trượt (thuốc, chi nhánh), thẻ nhà thuốc trang chủ, dữ liệu popup bản đồ và lệnh nạp nhiều ảnh mẫu."""

import datetime
from io import StringIO
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ung_dung.kho.tests.du_lieu import tao_du_lieu

from ..models import AnhChiNhanh, AnhThuoc
from ..selectors import du_lieu_ban_do_chi_nhanh, lay_chi_nhanh_cong_khai
from ..services.anh import them_anh
from .test_anh_va_khuyen_mai import tep_anh


class BoAnhVaTheChiNhanhTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_trang_thuoc_co_bo_anh_truot_va_anh_nho_khi_nhieu_anh(self):
        d = self.d
        url = reverse("danh_muc:khach_thuoc_chi_tiet", args=[d.thuoc.ma_thuoc])
        them_anh(d.admin, "thuoc", d.thuoc, [tep_anh()])
        trang = self.client.get(url)
        self.assertContains(trang, "data-bo-anh")
        self.assertNotContains(trang, "bo-anh-nho")  # một ảnh: không có hàng ảnh nhỏ, không nút ‹ ›
        them_anh(d.admin, "thuoc", d.thuoc, [tep_anh(), tep_anh()])
        trang = self.client.get(url)
        self.assertContains(trang, "bo-anh-nho")
        self.assertContains(trang, "<span data-so-anh>1</span> / 3", html=False)
        self.assertContains(trang, "vendor/splide/splide.min.js")
        for anh in AnhThuoc.objects.filter(thuoc=d.thuoc):
            self.assertContains(trang, reverse("danh_muc:anh_thuoc", args=[anh.pk]))

    def test_trang_chi_nhanh_co_bo_anh_va_nut_chi_duong(self):
        d = self.d
        them_anh(d.admin, "chi_nhanh", d.cn, [tep_anh(), tep_anh()])
        trang = self.client.get(
            reverse("danh_muc:khach_chi_nhanh_chi_tiet", args=[d.cn.ma_chi_nhanh])
        )
        self.assertContains(trang, "bo-anh-phu-kin")
        self.assertContains(trang, "bo-anh-nho")
        self.assertContains(trang, f"{reverse('webgis:ban_do')}?chi_nhanh={d.cn.ma_chi_nhanh}")

    def test_trang_chu_the_nha_thuoc_co_anh_trang_thai_va_xem_chi_tiet(self):
        d = self.d
        them_anh(d.admin, "chi_nhanh", d.cn, [tep_anh(), tep_anh()])
        trang = self.client.get("/")
        anh_dau = AnhChiNhanh.objects.filter(chi_nhanh=d.cn).order_by("thu_tu", "pk").first()
        self.assertContains(trang, reverse("danh_muc:anh_chi_nhanh", args=[anh_dau.pk]))
        self.assertContains(trang, "2 ảnh")
        self.assertContains(trang, "Xem chi tiết")
        self.assertContains(
            trang, reverse("danh_muc:khach_chi_nhanh_chi_tiet", args=[d.cn.ma_chi_nhanh])
        )
        self.assertContains(trang, d.cn.so_dien_thoai or d.cn.dia_chi)
        self.assertRegex(trang.content.decode(), r"Đang mở cửa|Đã đóng cửa")

    def test_dang_mo_cua_theo_gio_viet_nam(self):
        cn = self.d.cn
        cn.gio_mo_cua, cn.gio_dong_cua = datetime.time(7), datetime.time(22)
        ngay = timezone.localdate()
        luc = lambda gio, phut=0: timezone.make_aware(  # noqa: E731
            datetime.datetime.combine(ngay, datetime.time(gio, phut))
        )
        self.assertFalse(cn.dang_mo_cua(luc(6, 59)))
        self.assertTrue(cn.dang_mo_cua(luc(7)))
        self.assertTrue(cn.dang_mo_cua(luc(21, 59)))
        self.assertFalse(cn.dang_mo_cua(luc(22)))

    def test_du_lieu_popup_ban_do_co_moi_anh_theo_thu_tu(self):
        d = self.d
        them_anh(d.admin, "chi_nhanh", d.cn, [tep_anh(), tep_anh(), tep_anh()])
        cn = lay_chi_nhanh_cong_khai().get(pk=d.cn.pk)
        with self.assertNumQueries(0):  # ảnh đã prefetch, không truy vấn thêm từng chi nhánh
            du_lieu = du_lieu_ban_do_chi_nhanh(cn)
        mong_doi = [
            reverse("danh_muc:anh_chi_nhanh", args=[pk])
            for pk in AnhChiNhanh.objects.filter(chi_nhanh=d.cn)
            .order_by("thu_tu", "pk")
            .values_list("pk", flat=True)
        ]
        self.assertEqual(du_lieu["cac_anh"], mong_doi)
        self.assertEqual(du_lieu["anh"], mong_doi[0])
        self.assertEqual(du_lieu["dang_mo_cua"], d.cn.dang_mo_cua())
        self.assertIsNone(du_lieu["khoang_cach_met"])
        trang = self.client.get(reverse("webgis:ban_do"))
        self.assertContains(trang, '"cac_anh": [')
        self.assertContains(trang, "vendor/splide/splide.min.js")


class NapNhieuAnhMauTests(TestCase):
    """Lệnh nap_anh_that nạp đủ bộ ảnh mẫu cho mỗi chi nhánh, chạy lại không nhân đôi."""

    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_nap_du_bo_anh_chi_nhanh_va_chay_lai_khong_them(self):
        from django.core.management import call_command

        from ..anh_that import NHOM_CHI_NHANH

        du_lieu = tep_anh().read()
        with mock.patch(
            "ung_dung.danh_muc.management.commands.nap_anh_that.Command._tai",
            return_value=du_lieu,
        ):
            call_command("nap_anh_that", stdout=StringIO())
            so_anh = AnhChiNhanh.objects.filter(chi_nhanh=self.d.cn).count()
            call_command("nap_anh_that", stdout=StringIO())
        self.assertEqual(so_anh, len(NHOM_CHI_NHANH[0]))
        self.assertGreater(so_anh, 1)
        self.assertEqual(AnhChiNhanh.objects.filter(chi_nhanh=self.d.cn).count(), so_anh)
        self.assertEqual(
            list(AnhChiNhanh.objects.filter(chi_nhanh=self.d.cn).values_list("thu_tu", flat=True)),
            list(range(so_anh)),
        )
