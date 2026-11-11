from io import StringIO

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
            (reverse("webgis:ban_do"), "Tìm nhà thuốc gần bạn"),
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


class NapThuocThucTeTests(TestCase):
    def test_lenh_nap_thay_mo_phong_va_khong_tao_anh_ai(self):
        from django.core.management import call_command

        from ung_dung.kho.models import TonKho
        from ung_dung.kho.services.mo_phong import tao_du_lieu_mo_phong
        from ung_dung.kho.tests.du_lieu import tao_du_lieu

        from ..models import AnhThuoc, KhuyenMai, Thuoc

        d = tao_du_lieu()
        tao_du_lieu_mo_phong(d.admin, mat_khau="Mat-khau-thu-2026!")
        call_command("nap_thuoc_thuc_te", stdout=StringIO())
        self.assertFalse(Thuoc.objects.filter(ma_thuoc__startswith="MP-T-").exists())
        panadol = Thuoc.objects.get(ma_thuoc="TA-PANADOL-500")
        self.assertEqual((panadol.nhom_atc.ma_nhom_atc, panadol.la_thuoc_ke_don), ("N02BE", False))
        # Ảnh thật nạp riêng bằng nap_anh_that; lệnh này không vẽ ảnh minh họa.
        self.assertEqual(AnhThuoc.objects.filter(thuoc=panadol).count(), 0)
        self.assertTrue(Thuoc.objects.get(ma_thuoc="TA-STILNOX-10").la_thuoc_ke_don)
        self.assertFalse(
            KhuyenMai.objects.filter(thuoc__la_thuoc_ke_don=True, dang_hoat_dong=True).exists()
        )
        self.assertTrue(TonKho.objects.filter(lo_thuoc__thuoc__ma_thuoc="TA-SMECTA-30").exists())
        so_lo = TonKho.objects.count()
        Thuoc.objects.filter(pk=panadol.pk).update(gia_ban=1500, mo_ta_ngan="Đã sửa giá")
        call_command("nap_thuoc_thuc_te", stdout=StringIO())
        self.assertEqual(TonKho.objects.count(), so_lo)
        panadol.refresh_from_db()
        self.assertEqual((panadol.gia_ban, panadol.mo_ta_ngan), (1500, "Đã sửa giá"))
        call_command("nap_thuoc_thuc_te", "--ghi-de", stdout=StringIO())
        panadol.refresh_from_db()
        self.assertEqual(panadol.gia_ban, 1200)
        trang = self.client.get(reverse("danh_muc:khach_thuoc_chi_tiet", args=["TA-PANADOL-500"]))
        self.assertContains(trang, "Paracetamol 500 mg")


class DanhGiaThuocTests(TestCase):
    def test_chi_khach_da_mua_duoc_danh_gia_va_quan_tri_an(self):
        from django.contrib.gis.geos import Point

        from ung_dung.ban_hang.services.dat_hang import dat_hang
        from ung_dung.ban_hang.services.don_hang import (
            giao_cho_van_chuyen,
            xac_nhan_da_giao,
            xac_nhan_don,
        )
        from ung_dung.kho.tests.du_lieu import tao_ton

        from ..models import DanhGiaThuoc

        d = tao_du_lieu()
        tao_ton(d, ngay=60, luong=20)
        url = reverse("danh_muc:khach_danh_gia_thuoc", args=[d.thuoc.ma_thuoc])
        self.client.force_login(d.khach)
        self.client.post(url, {"so_sao": 5, "noi_dung": "Tốt"})
        self.assertFalse(DanhGiaThuoc.objects.exists())
        don = dat_hang(
            d.khach,
            d.cn,
            [{"thuoc": d.thuoc, "so_luong": 1}],
            hinh_thuc_nhan="giao_hang",
            phuong_thuc_thanh_toan="cod",
            giao={
                "ten_nguoi_nhan": "A",
                "so_dien_thoai": "0901234567",
                "dia_chi": "Q1",
                "vi_tri": Point(106.7, 10.77, srid=4326),
                "khoang_cach_met": 900,
            },
        )
        xac_nhan_don(d.nv, don)
        giao_cho_van_chuyen(d.nv, don)
        xac_nhan_da_giao(d.khach, don)
        trang = self.client.get(reverse("danh_muc:khach_thuoc_chi_tiet", args=[d.thuoc.ma_thuoc]))
        self.assertContains(trang, "Gửi đánh giá")
        self.client.post(url, {"so_sao": 4, "noi_dung": "Giao nhanh"})
        self.client.post(url, {"so_sao": 5, "noi_dung": "Đỡ đau đầu"})
        dg = DanhGiaThuoc.objects.get()
        self.assertEqual((dg.so_sao, dg.noi_dung_danh_gia), (5, "Đỡ đau đầu"))
        self.client.post(url, {"so_sao": 9})
        self.assertEqual(DanhGiaThuoc.objects.get().so_sao, 5)
        self.client.logout()
        trang = self.client.get(reverse("danh_muc:khach_thuoc_chi_tiet", args=[d.thuoc.ma_thuoc]))
        self.assertContains(trang, "Đỡ đau đầu")
        self.assertContains(trang, "1 đánh giá")
        DanhGiaThuoc.objects.update(dang_hien_thi=False)
        trang = self.client.get(reverse("danh_muc:khach_thuoc_chi_tiet", args=[d.thuoc.ma_thuoc]))
        self.assertNotContains(trang, "Đỡ đau đầu")
