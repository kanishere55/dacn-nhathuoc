from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from ung_dung.danh_muc.models import ChiNhanh


class DanhMucTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.quan_tri = get_user_model().objects.create_superuser("quan_tri_danh_muc")

    def test_tao_chi_nhanh_va_htmx_tim_kiem(self):
        self.client.force_login(self.quan_tri)
        url = reverse("danh_muc:chi_nhanh_tao")
        phan_hoi = self.client.post(
            url,
            {
                "ma_chi_nhanh": "CN-MOI",
                "ten_chi_nhanh": "Chi nhánh thử",
                "dia_chi": "TP.HCM",
                "kinh_do": "106.7",
                "vi_do": "10.77",
                "dang_hoat_dong": "on",
                "gio_mo_cua": "07:00",
                "gio_dong_cua": "22:00",
            },
        )
        self.assertEqual(phan_hoi.status_code, 302)
        self.assertEqual(ChiNhanh.objects.get().vi_tri.srid, 4326)
        phan_hoi = self.client.get(
            reverse("danh_muc:chi_nhanh_danh_sach"), {"q": "CN-MOI"}, headers={"HX-Request": "true"}
        )
        self.assertContains(phan_hoi, "Chi nhánh thử")
        self.assertNotContains(phan_hoi, "<html")
        self.assertIn("HX-Request", phan_hoi.headers["Vary"])

    def test_csdl_tu_choi_ma_chi_nhanh_sai_dinh_dang(self):
        with self.assertRaises(IntegrityError) as loi, transaction.atomic():
            ChiNhanh.objects.create(
                ma_chi_nhanh="cn-nhap-thuong",
                ten_chi_nhanh="Chi nhánh kiểm tra",
                dia_chi="TP.HCM",
                vi_tri=Point(106.7, 10.77, srid=4326),
            )
        self.assertEqual(loi.exception.__cause__.sqlstate, "23514")
        self.assertEqual(
            loi.exception.__cause__.diag.constraint_name,
            "kiem_tra__chi_nhanh__ma_dung_dinh_dang",
        )
