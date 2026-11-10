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
        self.assertEqual((pham_vi["so_phieu_ban"], pham_vi["tong_tien_ban"]), (1, 6000))
        self.assertEqual(dict(pham_vi["cac_luong"])["Viên"]["kha_dung"], 17)
        self.assertEqual(lay_bao_cao(d.admin, ngay, ngay)["tong_tien_ban"], 20000)
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
        self.assertEqual(lay_bao_cao(d.admin, ngay, ngay, d.cn2)["tong_tien_ban"], 14000)


class DoanhThuVaExcelTests(TestCase):
    def test_tru_hoan_kho_hoan_tien_va_xuat_excel(self):
        from io import BytesIO

        from django.contrib.gis.geos import Point
        from openpyxl import load_workbook

        from ung_dung.ban_hang.services.dat_hang import dat_hang
        from ung_dung.ban_hang.services.don_hang import huy_don, xac_nhan_don
        from ung_dung.ban_hang.services.phieu_ban import ban_tai_quay
        from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton

        d = tao_du_lieu()
        tao_ton(d, luong=50)
        ban_tai_quay(d.nv, d.cn, [{"thuoc": d.thuoc, "so_luong": 3}])
        don = dat_hang(
            d.khach,
            d.cn,
            [{"thuoc": d.thuoc, "so_luong": 5}],
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
        huy_don(d.nv, don, "Khách đổi ý")
        hom_nay = timezone.localdate()
        bao_cao = lay_bao_cao(d.ql, hom_nay, hom_nay)
        self.assertEqual((bao_cao["doanh_thu_gop"], bao_cao["tien_hoan_kho"]), (6000, 10000))
        self.assertEqual(bao_cao["ban_chay"][0]["tong_so_luong"], 3)
        self.client.force_login(d.ql)
        phan_hoi = self.client.get(reverse("bao_cao:tong_hop") + "?xuat=xlsx")
        self.assertIn("spreadsheetml", phan_hoi["Content-Type"])
        so = load_workbook(BytesIO(phan_hoi.content))
        self.assertEqual(so.sheetnames, ["Tổng hợp", "Thuốc bán chạy", "Biến động kho"])
        self.assertEqual(so["Tổng hợp"]["B6"].value, 6000)

    def test_hoan_tien_huy_don_khong_tru_hai_lan_va_excel_khong_chay_cong_thuc(self):
        from io import BytesIO

        from django.contrib.gis.geos import Point
        from openpyxl import load_workbook

        from ung_dung.ban_hang.services.dat_hang import dat_hang
        from ung_dung.ban_hang.services.don_hang import huy_don, xac_nhan_don
        from ung_dung.thanh_toan.services.ghi import ghi_ngay

        d = tao_du_lieu()
        tao_ton(d, luong=50)
        d.thuoc.ten_thuoc = "=1+1"
        d.thuoc.save(update_fields=["ten_thuoc"])
        ban_tai_quay(d.nv, d.cn, [{"thuoc": d.thuoc, "so_luong": 3}])
        don = dat_hang(
            d.khach,
            d.cn,
            [{"thuoc": d.thuoc, "so_luong": 5}],
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
        # Khách đã trả trước rồi đơn bị hủy sau khi xuất: phiếu bán bị loại qua hoàn kho,
        # khoản hoàn của chính đơn đó không được trừ thêm lần nữa.
        ghi_ngay(loai="thu", phuong_thuc="chuyen_khoan", so_tien=10000, don_hang=don)
        huy_don(d.nv, don, "Khách đổi ý")
        ghi_ngay(loai="hoan", phuong_thuc="chuyen_khoan", so_tien=10000, don_hang=don, nguoi=d.ql)
        hom_nay = timezone.localdate()
        bao_cao = lay_bao_cao(d.ql, hom_nay, hom_nay)
        self.assertEqual(bao_cao["doanh_thu_gop"], 6000)
        self.assertEqual(bao_cao["tien_hoan_khach"], 10000)
        self.assertEqual(bao_cao["tien_hoan_tra_hang"], 0)
        self.assertEqual(bao_cao["doanh_thu_thuan"], 6000)

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
        tao_ton(d, luong=50)
        hom_nay = timezone.localdate()
        cu = ban_tai_quay(d.nv, d.cn, [{"thuoc": d.thuoc, "so_luong": 2}])
        PhieuBan.objects.filter(pk=cu.pk).update(thoi_diem_tao=timezone.now() - timedelta(days=7))
        ban_tai_quay(d.nv, d.cn, [{"thuoc": d.thuoc, "so_luong": 3}])
        bao_cao = lay_bao_cao(d.ql, hom_nay - timedelta(days=6), hom_nay)
        bieu_do = bao_cao["bieu_do"]
        self.assertEqual(bieu_do["don_vi_thoi_gian"], "ngay")
        self.assertEqual(len(bieu_do["theo_thoi_gian"]), 7)
        self.assertEqual(bieu_do["theo_thoi_gian"][-1]["doanh_thu"], 6000)
        self.assertEqual(bieu_do["theo_kenh"], [{"ten": "Bán tại quầy", "doanh_thu": 6000.0}])
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
