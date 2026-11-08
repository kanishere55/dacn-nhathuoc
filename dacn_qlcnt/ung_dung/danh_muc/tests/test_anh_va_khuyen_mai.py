from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from ung_dung.chung.anh import xu_ly_anh
from ung_dung.kho.tests.du_lieu import tao_du_lieu

from ..gia import tinh_don_gia
from ..models import AnhThuoc, DanhMucSanPham, KhuyenMai
from ..selectors import lay_thuoc_cong_khai
from ..services.anh import dat_anh_dai_dien, them_anh
from ..services.danh_muc import luu_danh_muc


def tep_anh(rong=2400, cao=1200, dinh_dang="JPEG", exif=True):
    anh = Image.new("RGB", (rong, cao), (20, 120, 90))
    du_lieu = BytesIO()
    them = {}
    if exif:
        thong_tin = Image.Exif()
        thong_tin[0x010F] = "May anh thu"  # Make
        them["exif"] = thong_tin
    anh.save(du_lieu, dinh_dang, **them)
    return SimpleUploadedFile("anh.jpg", du_lieu.getvalue(), content_type="image/jpeg")


class AnhTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_chuan_hoa_webp_bo_metadata_va_thu_nho(self):
        du_lieu, rong, cao, bam = xu_ly_anh(tep_anh())
        self.assertEqual((rong, cao), (1600, 800))
        anh = Image.open(BytesIO(du_lieu))
        self.assertEqual(anh.format, "WEBP")
        self.assertFalse(anh.getexif())
        self.assertEqual(len(bam), 64)

    def test_tu_choi_tep_khong_phai_anh(self):
        with self.assertRaises(ValidationError):
            xu_ly_anh(SimpleUploadedFile("gia.jpg", b"%PDF-1.7 khong phai anh"))

    def test_luu_bytea_phuc_vu_cong_khai_va_etag(self):
        cac_anh = them_anh(self.d.admin, "thuoc", self.d.thuoc, [tep_anh(), tep_anh(300, 300)])
        url = reverse("danh_muc:anh_thuoc", args=[cac_anh[0].pk])
        phan_hoi = self.client.get(url)
        self.assertEqual(phan_hoi["Content-Type"], "image/webp")
        self.assertEqual(
            phan_hoi.content, bytes(AnhThuoc.objects.get(pk=cac_anh[0].pk).noi_dung_anh)
        )
        self.assertEqual(self.client.get(url, HTTP_IF_NONE_MATCH=phan_hoi["ETag"]).status_code, 304)
        dat_anh_dai_dien(self.d.admin, "thuoc", self.d.thuoc, cac_anh[1].pk)
        self.assertEqual(
            lay_thuoc_cong_khai().get(pk=self.d.thuoc.pk).id_anh_dai_dien, cac_anh[1].pk
        )

    def test_chi_quan_tri_duoc_tai_anh_qua_trang(self):
        url = reverse("danh_muc:anh_tai_len", args=["thuoc", self.d.thuoc.pk])
        self.client.force_login(self.d.nv)
        self.assertEqual(self.client.post(url, {"cac_anh": [tep_anh()]}).status_code, 403)
        self.client.force_login(self.d.admin)
        self.client.post(url, {"cac_anh": [tep_anh(), tep_anh(500, 500)]})
        self.assertEqual(AnhThuoc.objects.filter(thuoc=self.d.thuoc).count(), 2)


class GiaVaKhuyenMaiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_lam_tron_den_dong(self):
        self.assertEqual(tinh_don_gia(Decimal("12345"), 15), Decimal("10493"))
        self.assertEqual(tinh_don_gia(Decimal("2000"), 0), Decimal("2000"))

    def tao(self, ma, bat_dau, ket_thuc, phan_tram=10, dang_hoat_dong=True):
        return luu_danh_muc(
            self.d.admin,
            "khuyen_mai",
            {
                "ma_khuyen_mai": ma,
                "ten_khuyen_mai": "Ưu đãi",
                "thuoc": self.d.thuoc,
                "phan_tram_giam": phan_tram,
                "ngay_bat_dau": bat_dau,
                "ngay_ket_thuc": ket_thuc,
                "dang_hoat_dong": dang_hoat_dong,
            },
        )

    def test_khong_cho_hai_dot_trung_ngay(self):
        hom_nay = timezone.localdate()
        self.tao("KM1", hom_nay, hom_nay + timedelta(days=5))
        with self.assertRaisesMessage(ValidationError, "KM1"):
            self.tao("KM2", hom_nay + timedelta(days=5), hom_nay + timedelta(days=9))
        self.tao("KM3", hom_nay + timedelta(days=6), hom_nay + timedelta(days=9))
        self.tao("KM4", hom_nay, hom_nay, dang_hoat_dong=False)
        self.assertEqual(KhuyenMai.objects.count(), 3)

    def test_gia_khach_thay_va_loc(self):
        hom_nay = timezone.localdate()
        self.tao("KM1", hom_nay - timedelta(days=1), hom_nay + timedelta(days=1), phan_tram=15)
        thuoc = lay_thuoc_cong_khai(dang_giam=True).get()
        self.assertEqual((thuoc.phan_tram_giam, thuoc.don_gia), (15, Decimal("1700")))
        phan_hoi = self.client.get(reverse("danh_muc:khach_thuoc_chi_tiet", args=["THUOC1"]))
        self.assertContains(phan_hoi, "1.700 đ")
        self.assertContains(phan_hoi, "2.000 đ")

    def test_loc_danh_muc_va_thuoc_ke_don(self):
        dm = DanhMucSanPham.objects.create(ma_danh_muc_san_pham="DM1", ten_danh_muc_san_pham="Thử")
        self.d.thuoc.danh_muc_san_pham = dm
        self.d.thuoc.la_thuoc_ke_don = True
        self.d.thuoc.save()
        self.assertEqual(lay_thuoc_cong_khai(ma_danh_muc="DM1").count(), 1)
        self.assertEqual(lay_thuoc_cong_khai(khong_ke_don=True).count(), 0)
        phan_hoi = self.client.get(reverse("danh_muc:khach_thuoc_chi_tiet", args=["THUOC1"]))
        self.assertContains(phan_hoi, "không bán qua giao hàng")
