from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ung_dung.ban_hang.services.phieu_ban import ban_tai_quay
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton

from ..selectors import lay_bao_cao


class BaoCaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_bao_cao_dung_tien_va_phan_pham_vi_chi_nhanh(self):
        d = self.d
        tao_ton(d, "LO-1", luong=20)
        tao_ton(d, "LO-2", luong=20, chi_nhanh=d.cn2)
        ban_tai_quay(d.nv, d.cn, [{"thuoc": d.thuoc, "so_luong": 3}])
        ban_tai_quay(d.ql2, d.cn2, [{"thuoc": d.thuoc, "so_luong": 7}])
        ngay = timezone.localdate()
        pham_vi = lay_bao_cao(d.ql, ngay, ngay)
        self.assertEqual((pham_vi["so_phieu_ban"], pham_vi["doanh_thu"]), (1, 6000))
        self.assertEqual(dict(pham_vi["cac_luong"])["Viên"]["kha_dung"], 17)
        self.assertEqual(lay_bao_cao(d.admin, ngay, ngay)["doanh_thu"], 20000)
        self.client.force_login(d.ql)
        self.assertContains(self.client.get(reverse("bao_cao:tong_hop")), "Chứng từ trong kỳ")
        tra_ve = self.client.get(
            reverse("bao_cao:tong_hop"),
            {"tu_ngay": ngay.isoformat(), "den_ngay": ngay.isoformat(), "chi_nhanh": d.cn2.pk},
            headers={"HX-Request": "true"},
        )
        self.assertContains(tra_ve, "Bộ lọc chưa hợp lệ")
        self.assertNotContains(tra_ve, "<html")

        d.cn2.dang_hoat_dong = False
        d.cn2.save(update_fields=["dang_hoat_dong"])
        self.client.force_login(d.admin)
        tra_ve = self.client.get(
            reverse("bao_cao:tong_hop"),
            {"tu_ngay": ngay.isoformat(), "den_ngay": ngay.isoformat(), "chi_nhanh": d.cn2.pk},
        )
        self.assertContains(tra_ve, "Chứng từ trong kỳ")
        self.assertNotContains(tra_ve, "Bộ lọc chưa hợp lệ")
        self.assertEqual(lay_bao_cao(d.admin, ngay, ngay, d.cn2)["doanh_thu"], 14000)


class DoanhThuVaExcelTests(TestCase):
    def test_tham_so_la_tren_url_van_hien_bao_cao_mac_dinh(self):
        self.client.force_login(tao_du_lieu().ql)
        tra_ve = self.client.get(reverse("bao_cao:tong_hop"), {"utm_source": "email"})
        self.assertContains(tra_ve, "Chứng từ trong kỳ")
        self.assertNotContains(tra_ve, "Bộ lọc chưa hợp lệ")

    def test_don_dat_giu_chi_tinh_khi_khach_nhan_va_xuat_excel(self):
        from io import BytesIO

        from openpyxl import load_workbook

        from ung_dung.ban_hang.services.dat_hang import dat_giu
        from ung_dung.ban_hang.services.don_hang import huy_don

        d = tao_du_lieu()
        tao_ton(d, ngay=60, luong=50)
        ban_tai_quay(d.nv, d.cn, [{"thuoc": d.thuoc, "so_luong": 3}])
        # Đơn bị hủy không có phiếu bán nên không tính doanh thu.
        huy_don(d.khach, dat_giu(d.khach, d.cn, [{"thuoc": d.thuoc, "so_luong": 4}]))
        don = dat_giu(d.khach, d.cn, [{"thuoc": d.thuoc, "so_luong": 5}])
        ban_tai_quay(d.nv, d.cn, [], don_hang=don, phuong_thuc_thanh_toan="chuyen_khoan")
        hom_nay = timezone.localdate()
        bao_cao = lay_bao_cao(d.ql, hom_nay, hom_nay)
        self.assertEqual(bao_cao["doanh_thu"], 16000)
        self.assertEqual((bao_cao["so_don_giu"], bao_cao["so_don_da_nhan"]), (2, 1))
        self.assertEqual(
            dict(bao_cao["theo_phuong_thuc"]), {"Tiền mặt": 6000, "Chuyển khoản": 10000}
        )
        self.assertEqual(
            {k["ten"]: k["doanh_thu"] for k in bao_cao["bieu_do"]["theo_kenh"]},
            {"Bán trực tiếp tại quầy": 6000.0, "Đặt giữ trên website": 10000.0},
        )
        self.client.force_login(d.ql)
        phan_hoi = self.client.get(reverse("bao_cao:tong_hop") + "?xuat=xlsx")
        self.assertIn("spreadsheetml", phan_hoi["Content-Type"])
        so = load_workbook(BytesIO(phan_hoi.content))
        self.assertEqual(so.sheetnames, ["Tổng hợp", "Thuốc bán chạy", "Biến động kho"])
        self.assertEqual(so["Tổng hợp"]["B6"].value, 16000)

    def test_excel_khong_chay_cong_thuc_trong_ten_thuoc(self):
        from io import BytesIO

        from openpyxl import load_workbook

        d = tao_du_lieu()
        tao_ton(d, ngay=60, luong=50)
        d.thuoc.ten_thuoc = "=1+1"
        d.thuoc.save(update_fields=["ten_thuoc"])
        ban_tai_quay(d.nv, d.cn, [{"thuoc": d.thuoc, "so_luong": 3}])
        self.client.force_login(d.ql)
        so = load_workbook(
            BytesIO(self.client.get(reverse("bao_cao:tong_hop") + "?xuat=xlsx").content)
        )
        o_ten = [o for dong in so["Thuốc bán chạy"].iter_rows() for o in dong if o.value == "=1+1"]
        self.assertTrue(o_ten)
        self.assertTrue(all(o.data_type == "s" for o in o_ten))


class BieuDoBaoCaoTests(TestCase):
    def test_bieu_do_theo_ngay_kenh_va_so_sanh_ky_truoc(self):
        from datetime import timedelta

        from ung_dung.ban_hang.models import PhieuBan

        d = tao_du_lieu()
        tao_ton(d, ngay=60, luong=50)
        hom_nay = timezone.localdate()
        cu = ban_tai_quay(d.nv, d.cn, [{"thuoc": d.thuoc, "so_luong": 2}])
        PhieuBan.objects.filter(pk=cu.pk).update(thoi_diem_tao=timezone.now() - timedelta(days=7))
        ban_tai_quay(d.nv, d.cn, [{"thuoc": d.thuoc, "so_luong": 3}])
        bao_cao = lay_bao_cao(d.ql, hom_nay - timedelta(days=6), hom_nay)
        bieu_do = bao_cao["bieu_do"]
        self.assertEqual(bieu_do["don_vi_thoi_gian"], "ngay")
        self.assertEqual(len(bieu_do["theo_thoi_gian"]), 7)
        self.assertEqual(bieu_do["theo_thoi_gian"][-1]["doanh_thu"], 6000)
        self.assertEqual(
            bieu_do["theo_kenh"], [{"ten": "Bán trực tiếp tại quầy", "doanh_thu": 6000.0}]
        )
        # Kỳ trước (7 ngày liền trước) có 4.000 đ, kỳ này 6.000 đ: tăng 50%.
        self.assertEqual(bao_cao["doanh_thu_ky_truoc"], 4000)
        self.assertEqual(bao_cao["thay_doi_doanh_thu"], 50)
        thang = lay_bao_cao(d.ql, hom_nay - timedelta(days=120), hom_nay)["bieu_do"]
        self.assertEqual(thang["don_vi_thoi_gian"], "thang")
        self.assertEqual(sum(m["doanh_thu"] for m in thang["theo_thoi_gian"]), 10000)
        self.client.force_login(d.ql)
        self.assertContains(
            self.client.get(reverse("bao_cao:tong_hop")), 'id="du-lieu-bieu-do-bao-cao"'
        )
