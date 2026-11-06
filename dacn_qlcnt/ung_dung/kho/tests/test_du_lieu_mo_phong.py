from django.contrib.auth import get_user_model
from django.test import TestCase

from ung_dung.danh_muc.models import ChiNhanh, Thuoc
from ung_dung.kho.services.mo_phong import tao_du_lieu_mo_phong


class DuLieuMoPhongTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.quan_tri = get_user_model().objects.create_superuser("quan_tri_mo_phong")

    def test_sinh_mo_phong_ghi_db_va_khong_ghi_lap(self):
        tao_du_lieu_mo_phong(self.quan_tri)
        self.assertEqual(ChiNhanh.objects.count(), 3)
        self.assertEqual(Thuoc.objects.count(), 8)
        with self.assertRaises(ValueError):
            tao_du_lieu_mo_phong(self.quan_tri)
        self.assertEqual(ChiNhanh.objects.count(), 3)
