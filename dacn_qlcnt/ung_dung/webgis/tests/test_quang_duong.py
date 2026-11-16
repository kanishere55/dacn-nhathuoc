"""Quãng đường đi thực tế (OSRM) từ vị trí của khách: sắp gần nhất, ước tính khi OSRM lỗi, bộ nhớ đệm."""

from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from ung_dung.kho.tests.du_lieu import tao_du_lieu

from ..services.duong_di import HE_SO_UOC_TINH, quang_duong_tu_vi_tri

GOI_OSRM = "ung_dung.webgis.services.duong_di._goi_osrm_tu_vi_tri"
VI_TRI = {"vi_do": 10.7801, "kinh_do": 106.7101}


class QuangDuongTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_sap_theo_quang_duong_thuc_te_khi_khac_thu_tu_postgis(self):
        url = reverse("webgis:chi_nhanh_gan")
        thang = self.client.get(url, VI_TRI).json()["ket_qua"]
        self.assertEqual([cn["ma_chi_nhanh"] for cn in thang], ["CN2", "CN1"])
        cache.clear()
        # Theo đường bộ CN1 lại gần hơn (đường một chiều, sông...): danh sách đổi theo OSRM.
        with mock.patch(GOI_OSRM, return_value=[5200, 2100]) as goi:
            gan = self.client.get(url, VI_TRI).json()["ket_qua"]
        goi.assert_called_once()
        self.assertEqual([cn["ma_chi_nhanh"] for cn in gan], ["CN1", "CN2"])
        self.assertEqual(gan[0]["quang_duong_met"], 2100)
        self.assertEqual(gan[0]["phut_xe_may"], 4)  # 2,1 km ở 28 km/giờ
        self.assertFalse(gan[0]["quang_duong_uoc_tinh"])

    def test_osrm_loi_thi_uoc_tinh_va_khong_lam_hong_trang(self):
        with mock.patch(GOI_OSRM, side_effect=TimeoutError):
            gan = self.client.get(reverse("webgis:chi_nhanh_gan"), VI_TRI).json()["ket_qua"]
        self.assertTrue(all(cn["quang_duong_uoc_tinh"] for cn in gan))
        for cn in gan:
            self.assertEqual(cn["quang_duong_met"], round(cn["khoang_cach_met"] * HE_SO_UOC_TINH))

    def test_bo_nho_dem_khong_goi_lai_osrm_cung_vi_tri(self):
        cn = self.d.cn
        diem = [(cn.pk, cn.vi_tri, 1000)]
        with mock.patch(GOI_OSRM, return_value=[1500]) as goi:
            quang_duong_tu_vi_tri(cn.vi_tri, diem)
            ket_qua = quang_duong_tu_vi_tri(cn.vi_tri, diem)
        self.assertEqual(goi.call_count, 1)
        self.assertEqual(ket_qua[cn.pk]["quang_duong_met"], 1500)
        self.assertEqual(quang_duong_tu_vi_tri(cn.vi_tri, []), {})
