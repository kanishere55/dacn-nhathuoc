from datetime import timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from ung_dung.kho.tests.du_lieu import tao_du_lieu

from ..models import BannerTrangChu, ThongTinCuaHang, TrangNoiDung


def anh(mau=(30, 120, 90)):
    dem = BytesIO()
    Image.new("RGB", (300, 200), mau).save(dem, "PNG")
    return SimpleUploadedFile("b.png", dem.getvalue(), content_type="image/png")


def tao_banner(**them):
    banner = BannerTrangChu(
        **{"tieu_de": "Giao thuốc tận nhà", "nhan_nut": "Mua ngay", "duong_dan": "/thuoc/", **them}
    )
    banner.gan_du_lieu(anh())
    banner.save()
    return banner


class NoiDungTests(TestCase):
    def setUp(self):
        self.d = tao_du_lieu()

    def test_trang_chu_chi_hien_banner_trong_han(self):
        hom_nay = timezone.localdate()
        tao_banner(mau_nen="#fdf0dd", thu_tu=1)
        tao_banner(tieu_de="Hết hạn", ngay_ket_thuc=hom_nay - timedelta(days=1))
        tao_banner(tieu_de="Đang ẩn", dang_hien_thi=False)
        trang = self.client.get(reverse("chung:trang_chu"))
        self.assertContains(trang, "data-bang-chuyen")
        self.assertContains(trang, "--mau-hero: #fdf0dd")
        self.assertNotContains(trang, "Hết hạn")
        self.assertNotContains(trang, "Đang ẩn")

    def test_quan_tri_tao_banner_va_kiem_du_lieu(self):
        self.client.force_login(self.d.admin)
        url = reverse("noi_dung:banner_tao")
        du_lieu = {
            "tieu_de": "Vitamin cho cả nhà",
            "nhan_nut": "Xem ngay",
            "duong_dan": "https://ngoai.example.com",
            "mau_nen": "#E6EEF9",
            "thu_tu": 0,
            "dang_hien_thi": "on",
        }
        phan_hoi = self.client.post(url, du_lieu)
        self.assertFalse(BannerTrangChu.objects.exists())
        self.assertContains(phan_hoi, "Banner mới cần ảnh")
        du_lieu.update(duong_dan="/thuoc/?q=vitamin", anh=anh())
        self.client.post(url, du_lieu)
        banner = BannerTrangChu.objects.get()
        self.assertEqual(banner.mau_nen, "#e6eef9")
        self.assertEqual(
            self.client.get(reverse("noi_dung:anh_banner", args=[banner.pk]))["Content-Type"],
            "image/webp",
        )
        self.client.force_login(self.d.ql)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_trang_chinh_sach_va_thong_tin_cua_hang(self):
        TrangNoiDung.objects.create(
            duong_dan_trang="huong-dan-dat-giu",
            tieu_de="Hướng dẫn đặt giữ",
            noi_dung_trang="<p>Giữ hàng <strong>24 giờ</strong></p>",
        )
        ThongTinCuaHang.objects.create(
            ten_thuong_hieu="Nhà thuốc Thử",
            hotline="02839000000",
            email_lien_he="lienhe@example.com",
            dia_chi_tru_so="TP.HCM",
            gio_lam_viec="07:00–22:00",
        )
        trang = self.client.get(reverse("noi_dung:trang", args=["huong-dan-dat-giu"]))
        self.assertContains(trang, "<strong>24 giờ</strong>", html=True)
        self.assertContains(trang, "Nhà thuốc Thử")
        self.assertContains(trang, "02839000000")
        self.client.force_login(self.d.admin)
        phan_hoi = self.client.post(
            reverse("noi_dung:trang_sua", args=[TrangNoiDung.objects.get().pk]),
            {
                "tieu_de": "Đặt giữ",
                "duong_dan_trang": "huong-dan-dat-giu",
                "noi_dung_trang": '<p onclick="x()">Mới</p><script>a</script>',
                "thu_tu": 0,
            },
        )
        self.assertEqual(phan_hoi.status_code, 302)
        trang_nd = TrangNoiDung.objects.get()
        self.assertEqual((trang_nd.noi_dung_trang, trang_nd.dang_hien_thi), ("<p>Mới</p>", False))
        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("noi_dung:trang", args=["huong-dan-dat-giu"])).status_code, 404
        )
