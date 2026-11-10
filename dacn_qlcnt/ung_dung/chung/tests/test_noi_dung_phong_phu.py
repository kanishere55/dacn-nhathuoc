from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from ung_dung.kho.tests.du_lieu import tao_du_lieu

from ..noi_dung_phong_phu import hien_thi, lam_sach_html, van_ban_thanh_html


class LamSachTests(SimpleTestCase):
    def test_bo_the_va_thuoc_tinh_nguy_hiem(self):
        sach = lam_sach_html(
            '<p class="ql-align-center x" onclick="a()">Uống <strong>sau ăn</strong></p>'
            "<script>alert(1)</script><img src=x onerror=a()>"
            '<a href="javascript:alert(1)">x</a><a href="https://dav.gov.vn">Cục Quản lý Dược</a>'
            "<p><br></p>"
        )
        self.assertNotIn("script", sach)
        self.assertNotIn("onclick", sach)
        self.assertNotIn("<img", sach)
        self.assertNotIn("javascript", sach)
        self.assertIn('<p class="ql-align-center">Uống <strong>sau ăn</strong></p>', sach)
        self.assertIn('href="https://dav.gov.vn"', sach)
        self.assertIn("noopener", sach)
        self.assertFalse(sach.endswith("<p><br></p>"))

    def test_van_ban_cu_thanh_doan(self):
        self.assertEqual(
            van_ban_thanh_html("Dòng 1\nDòng <2>\n\nĐoạn hai"),
            "<p>Dòng 1<br>Dòng &lt;2&gt;</p><p>Đoạn hai</p>",
        )
        self.assertEqual(hien_thi("Uống 1 viên"), "<p>Uống 1 viên</p>")
        self.assertEqual(hien_thi(""), "")


class TrinhSoanThaoTrenFormTests(TestCase):
    def test_luu_noi_dung_dinh_dang_va_hien_cho_khach(self):
        d = tao_du_lieu()
        self.client.force_login(d.admin)
        url = reverse("danh_muc:thuoc_sua", args=[d.thuoc.pk])
        trang = self.client.get(url)
        self.assertContains(trang, "data-trinh-soan-thao")
        self.assertContains(trang, "vendor/quill/quill.min.js")
        du_lieu = {
            ten: (gia_tri.pk if hasattr(gia_tri, "pk") else gia_tri)
            for ten, gia_tri in trang.context["form"].initial.items()
            if gia_tri is not None
        }
        du_lieu.update(
            noi_dung_chi_tiet="<h2>Chỉ định</h2><ul><li>Hạ sốt</li><li>Giảm đau</li></ul><script>x</script>",
            dang_hoat_dong="on",
        )
        du_lieu.pop("la_thuoc_ke_don", None)
        phan_hoi = self.client.post(url, du_lieu)
        self.assertEqual(
            phan_hoi.status_code,
            302,
            getattr(phan_hoi, "context", {}) and phan_hoi.context["form"].errors,
        )
        d.thuoc.refresh_from_db()
        self.assertEqual(
            d.thuoc.noi_dung_chi_tiet, "<h2>Chỉ định</h2><ul><li>Hạ sốt</li><li>Giảm đau</li></ul>"
        )
        khach = self.client.get(reverse("danh_muc:khach_thuoc_chi_tiet", args=[d.thuoc.ma_thuoc]))
        self.assertContains(khach, "<li>Giảm đau</li>", html=False)
