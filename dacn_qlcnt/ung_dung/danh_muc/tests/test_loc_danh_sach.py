from django.test import TestCase
from django.urls import reverse

from ung_dung.chung.templatetags.loc_trang import cac_so_trang
from ung_dung.kho.tests.du_lieu import tao_du_lieu

from ..models import AnhThuoc, DanhMucSanPham, Thuoc
from ..services.anh import them_anh
from .test_anh_va_khuyen_mai import tep_anh


class LocDanhMucQuanLyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        cls.dm = DanhMucSanPham.objects.create(
            ma_danh_muc_san_pham="GIAM-DAU", ten_danh_muc_san_pham="Giảm đau"
        )
        for so in range(30):
            Thuoc.objects.create(
                ma_thuoc=f"T{so:03d}",
                ten_thuoc=f"Thuốc số {so:03d}",
                nhom_atc=cls.d.nhom,
                don_vi_tinh=cls.d.dvt,
                ham_luong="10 mg",
                dang_bao_che="Viên",
                nha_san_xuat="Hãng X",
                gia_ban=1000,
                danh_muc_san_pham=cls.dm if so < 5 else None,
                dang_hoat_dong=so % 2 == 0,
            )

    def setUp(self):
        self.client.force_login(self.d.admin)
        self.url = reverse("danh_muc:thuoc_danh_sach")

    def test_phan_trang_va_chon_so_dong(self):
        trang = self.client.get(self.url, {"moi_trang": 10})
        self.assertEqual(len(trang.context["cac_dong"]), 10)
        self.assertEqual(trang.context["trang"].paginator.count, 31)
        self.assertContains(trang, "Hiển thị 1–10 / 31 mục")
        trang_hai = self.client.get(self.url, {"moi_trang": 10, "page": 2})
        self.assertContains(trang_hai, "moi_trang=10")

    def test_loc_theo_danh_muc_thuong_trang_thai_va_tim_kiem(self):
        trang = self.client.get(self.url, {"danh_muc": self.dm.pk})
        self.assertEqual(trang.context["trang"].paginator.count, 5)
        trang = self.client.get(self.url, {"danh_muc": self.dm.pk, "trang_thai": "khong"})
        self.assertEqual(trang.context["trang"].paginator.count, 2)
        trang = self.client.get(self.url, {"tim": "số 007"})
        self.assertEqual(trang.context["trang"].paginator.count, 1)
        trang = self.client.get(self.url, {"danh_muc": "khong-ton-tai"})
        self.assertEqual(trang.context["trang"].paginator.count, 31)

    def test_loc_theo_co_anh_va_hien_anh_thu_nho(self):
        thuoc = Thuoc.objects.get(ma_thuoc="T002")
        anh = them_anh(self.d.admin, "thuoc", thuoc, [tep_anh()])[0]
        trang = self.client.get(self.url, {"co_anh": "co"})
        self.assertEqual(trang.context["trang"].paginator.count, 1)
        self.assertContains(trang, reverse("danh_muc:anh_thuoc", args=[anh.pk]))
        trang = self.client.get(self.url, {"co_anh": "khong"})
        self.assertEqual(trang.context["trang"].paginator.count, 30)
        self.assertEqual(AnhThuoc.objects.count(), 1)

    def test_anh_thuoc_ngung_hoat_dong_chi_nhan_su_xem_duoc(self):
        thuoc = Thuoc.objects.get(ma_thuoc="T001")
        self.assertFalse(thuoc.dang_hoat_dong)
        anh = them_anh(self.d.admin, "thuoc", thuoc, [tep_anh()])[0]
        url = reverse("danh_muc:anh_thuoc", args=[anh.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_cac_danh_sach_khac_deu_co_thanh_loc(self):
        for ten in (
            "chi_nhanh",
            "nha_cung_cap",
            "nhan_vien",
            "quy_doi_bao_goi",
            "khuyen_mai",
            "danh_muc_san_pham",
            "nhom_atc",
            "don_vi_tinh",
        ):
            with self.subTest(danh_sach=ten):
                trang = self.client.get(reverse(f"danh_muc:{ten}_danh_sach"))
                self.assertContains(trang, 'class="thanh-loc"')

    def test_dai_so_trang_gon(self):
        trang = self.client.get(self.url, {"moi_trang": 10, "page": 3}).context["trang"]
        self.assertEqual(cac_so_trang(trang), [1, 2, 3, 4])


class LocKhoVaBanHangTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_cac_trang_danh_sach_kho_va_ban_hang_co_thanh_loc_va_phan_trang(self):
        self.client.force_login(self.d.admin)
        for ten in (
            "kho:ton_kho_danh_sach",
            "kho:lo_thuoc_danh_sach",
            "kho:phieu_nhap_danh_sach",
            "kho:phieu_tra_danh_sach",
            "kho:phieu_dieu_chuyen_danh_sach",
            "kho:phieu_kiem_ke_danh_sach",
            "kho:phieu_xuat_huy_danh_sach",
            "ban_hang:phieu_ban_danh_sach",
            "ban_hang:don_hang_danh_sach",
            "ban_hang:xuat_hoa_don_danh_sach",
            "tai_khoan:danh_sach",
        ):
            with self.subTest(trang=ten):
                phan_hoi = self.client.get(reverse(ten))
                self.assertEqual(phan_hoi.status_code, 200)
                self.assertContains(phan_hoi, 'class="thanh-loc"')
                self.assertContains(phan_hoi, 'class="phan-trang"')

    def test_don_hang_loc_chi_nhanh_va_giu_the_trang_thai(self):
        self.client.force_login(self.d.admin)
        phan_hoi = self.client.get(
            reverse("ban_hang:don_hang_danh_sach"),
            {"trang_thai": "hoan_thanh", "chi_nhanh": self.d.cn2.pk, "thoi_gian": "7_ngay"},
        )
        self.assertEqual(phan_hoi.status_code, 200)
        self.assertContains(phan_hoi, '<select name="chi_nhanh">')
        self.assertContains(phan_hoi, 'name="trang_thai" value="hoan_thanh"')
        loc = phan_hoi.context["loc"]
        self.assertEqual(
            {o.ten: o.gia_tri for o in loc.cac_o_chon}["chi_nhanh"], str(self.d.cn2.pk)
        )
