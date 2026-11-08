from django.test import TestCase
from django.urls import reverse

from ung_dung.kho.tests.du_lieu import tao_du_lieu

from ..models import NhomATC, Thuoc


class DanhMucKhachTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_khach_vang_lai_xem_duoc_cac_trang_cong_khai(self):
        d = self.d
        for url, noi_dung in (
            ("/", "Tìm nhà thuốc gần bạn"),
            (reverse("danh_muc:khach_thuoc_danh_sach"), d.thuoc.ten_thuoc),
            (reverse("danh_muc:khach_thuoc_chi_tiet", args=[d.thuoc.ma_thuoc]), d.thuoc.ham_luong),
            (reverse("danh_muc:khach_chi_nhanh_chi_tiet", args=[d.cn.ma_chi_nhanh]), d.cn.dia_chi),
            (reverse("webgis:ban_do"), "Tìm chi nhánh còn đủ thuốc"),
        ):
            with self.subTest(url=url):
                trang = self.client.get(url)
                self.assertContains(trang, noi_dung)
                self.assertNotContains(trang, 'class="thanh-ben"')
        self.assertContains(self.client.get("/"), d.nhom.ten_nhom_atc)

    def test_danh_muc_tim_loc_phan_trang_va_an_thuoc_ngung(self):
        d = self.d
        nhom_khac = NhomATC.objects.create(ma_nhom_atc="R03", ten_nhom_atc="Hô hấp")
        for so in range(15):
            Thuoc.objects.create(
                ma_thuoc=f"TRA-{so:02d}",
                ten_thuoc=f"Tra cứu {so:02d}",
                nhom_atc=nhom_khac if so == 14 else d.nhom,
                don_vi_tinh=d.dvt,
                ham_luong=d.thuoc.ham_luong,
                dang_bao_che=d.thuoc.dang_bao_che,
                nha_san_xuat=d.thuoc.nha_san_xuat,
                gia_ban=1000,
                dang_hoat_dong=so != 13,
            )
        url = reverse("danh_muc:khach_thuoc_danh_sach")
        trang = self.client.get(url, {"q": "Tra cứu", "nhom": d.nhom.ma_nhom_atc})
        self.assertEqual(trang.context["trang"].paginator.count, 13)
        self.assertContains(trang, "Trang sau")
        self.assertNotContains(trang, "TRA-13")
        trang_hai = self.client.get(url, {"q": "Tra cứu", "nhom": d.nhom.ma_nhom_atc, "page": 2})
        self.assertContains(trang_hai, "TRA-12")
        self.assertNotContains(trang_hai, "TRA-14")
        self.assertEqual(
            self.client.get(reverse("danh_muc:khach_thuoc_chi_tiet", args=["TRA-13"])).status_code,
            404,
        )
