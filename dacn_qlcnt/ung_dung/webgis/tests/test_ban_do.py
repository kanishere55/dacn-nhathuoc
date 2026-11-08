from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from ung_dung.ban_hang.services.dat_giu import dat_giu
from ung_dung.danh_muc.models import DonViTinh, Thuoc
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton


class WebGISTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_loc_postgis_va_ket_hop_luong_dang_giu(self):
        d = self.d
        tao_ton(d, "LO-GAN", luong=10)
        tao_ton(d, "LO-XA", luong=10, chi_nhanh=d.cn2)
        dat_giu(d.khach, d.cn, [{"thuoc": d.thuoc, "so_luong": 9}])
        yeu_cau = {
            "kinh_do": d.cn.vi_tri.x,
            "vi_do": d.cn.vi_tri.y,
            "ban_kinh_met": 5000,
            "cac_thuoc": [{"id_thuoc": d.thuoc.pk, "so_luong": 2}],
        }
        with CaptureQueriesContext(connection) as cac_truy_van:
            phan_hoi = self.client.post(
                reverse("webgis:tim_kiem"), yeu_cau, content_type="application/json"
            )
        self.assertEqual(phan_hoi.status_code, 200)
        self.assertEqual([k["id_chi_nhanh"] for k in phan_hoi.json()["ket_qua"]], [d.cn2.pk])
        sql = " ".join(q["sql"].lower() for q in cac_truy_van)
        self.assertIn("st_dwithin", sql)
        self.assertIn("st_distance", sql)
        yeu_cau["ban_kinh_met"] = 100
        phan_hoi = self.client.post(
            reverse("webgis:tim_kiem"), yeu_cau, content_type="application/json"
        )
        self.assertEqual(phan_hoi.json()["ket_qua"], [])

    def test_heatmap_chi_cong_cung_don_vi_va_chi_quan_tri_xem(self):
        d = self.d
        tao_ton(d, "LO-VIEN", luong=7)
        tao_ton(d, "LO-VIEN-HAI", luong=11, chi_nhanh=d.cn2)
        chai = DonViTinh.objects.create(ma_don_vi_tinh="CHAI", ten_don_vi_tinh="Chai")
        thuoc = Thuoc.objects.create(
            ma_thuoc="DUNG-DICH",
            ten_thuoc="Dung dịch thử",
            nhom_atc=d.nhom,
            don_vi_tinh=chai,
            ham_luong="10 ml",
            dang_bao_che="Dung dịch",
            nha_san_xuat="Mô phỏng",
            gia_ban=1000,
        )
        from types import SimpleNamespace

        tao_ton(SimpleNamespace(thuoc=thuoc, cn=d.cn), "LO-CHAI", luong=90)
        url = reverse("webgis:du_lieu_nhiet")
        loc = {"nhom_atc": d.nhom.pk, "don_vi_tinh": d.dvt.pk}
        self.client.force_login(d.nv)
        self.assertEqual(self.client.get(url, loc).status_code, 403)
        self.client.force_login(d.admin)
        self.assertContains(self.client.get(reverse("webgis:ban_do_nhiet")), "Bản đồ nhiệt")
        kq = self.client.get(url, loc).json()["ket_qua"]
        self.assertEqual(
            {p["ten_chi_nhanh"]: p["so_luong"] for p in kq},
            {d.cn.ten_chi_nhanh: 7, d.cn2.ten_chi_nhanh: 11},
        )
        d.cn2.dang_hoat_dong = False
        d.cn2.save(update_fields=["dang_hoat_dong"])
        kq = self.client.get(url, loc).json()["ket_qua"]
        self.assertEqual(
            {p["ten_chi_nhanh"]: p["so_luong"] for p in kq},
            {d.cn.ten_chi_nhanh: 7, d.cn2.ten_chi_nhanh: 0},
        )

    def test_trang_khach_render_va_api_giu_thanh_cong(self):
        d = self.d
        tao_ton(d)
        self.assertContains(self.client.get(reverse("webgis:ban_do")), "vendor/leaflet/leaflet.js")
        self.client.force_login(d.khach)
        self.assertContains(
            self.client.get(reverse("webgis:ban_do")), f'data-url-giu="{reverse("webgis:dat_giu")}"'
        )
        phan_hoi = self.client.post(
            reverse("webgis:dat_giu"),
            {"id_chi_nhanh": d.cn.pk, "cac_thuoc": [{"id_thuoc": d.thuoc.pk, "so_luong": 1}]},
            content_type="application/json",
        )
        self.assertEqual(phan_hoi.status_code, 201)
        self.assertContains(self.client.get(phan_hoi.json()["duong_dan"]), "thanh toán")
