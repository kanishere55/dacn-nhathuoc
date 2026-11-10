from django.test import TestCase
from django.urls import reverse

from ung_dung.chung.noi_dung_phong_phu import lam_sach_html
from ung_dung.kho.tests.du_lieu import tao_du_lieu

from ..models import AnhChiNhanh, AnhNoiDung, AnhThuoc
from ..services.anh import them_anh
from .test_anh_va_khuyen_mai import tep_anh

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class AnhKhongTaiLaiTrangTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def setUp(self):
        self.client.force_login(self.d.admin)

    def test_tai_len_ajax_tra_danh_sach_anh_moi(self):
        url = reverse("danh_muc:anh_tai_len", args=["thuoc", self.d.thuoc.pk])
        du_lieu = self.client.post(url, {"cac_anh": [tep_anh(), tep_anh(500, 500)]}, **AJAX).json()
        self.assertTrue(du_lieu["ok"])
        self.assertEqual(len(du_lieu["cac_anh"]), 2)
        self.assertTrue(du_lieu["cac_anh"][0]["la_dai_dien"])
        self.assertEqual(AnhThuoc.objects.filter(thuoc=self.d.thuoc).count(), 2)

    def test_xoa_va_dat_dai_dien_ajax_khong_chuyen_trang(self):
        cac_anh = them_anh(self.d.admin, "thuoc", self.d.thuoc, [tep_anh(), tep_anh()])
        phan_hoi = self.client.post(
            reverse("danh_muc:anh_dai_dien", args=["thuoc", self.d.thuoc.pk, cac_anh[1].pk]), **AJAX
        )
        self.assertEqual(phan_hoi.status_code, 200)
        self.assertEqual(phan_hoi.json()["cac_anh"][0]["id"], cac_anh[1].pk)
        phan_hoi = self.client.post(
            reverse("danh_muc:anh_xoa", args=["thuoc", self.d.thuoc.pk, cac_anh[1].pk]), **AJAX
        )
        self.assertEqual(phan_hoi.status_code, 200)
        self.assertEqual([a["id"] for a in phan_hoi.json()["cac_anh"]], [cac_anh[0].pk])

    def test_loi_ajax_tra_json_400(self):
        url = reverse("danh_muc:anh_tai_len", args=["chi_nhanh", self.d.cn.pk])
        phan_hoi = self.client.post(url, {}, **AJAX)
        self.assertEqual(phan_hoi.status_code, 400)
        self.assertFalse(phan_hoi.json()["ok"])

    def test_gui_form_thuong_van_chuyen_trang_nhu_cu(self):
        url = reverse("danh_muc:anh_tai_len", args=["chi_nhanh", self.d.cn.pk])
        phan_hoi = self.client.post(url, {"cac_anh": [tep_anh()]})
        self.assertRedirects(
            phan_hoi,
            reverse("danh_muc:chi_nhanh_sua", args=[self.d.cn.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(AnhChiNhanh.objects.filter(chi_nhanh=self.d.cn).count(), 1)

    def test_trang_sua_co_o_chon_anh_va_xem_truoc(self):
        for ten, doi_tuong in (("thuoc", self.d.thuoc), ("chi_nhanh", self.d.cn)):
            trang = self.client.get(reverse(f"danh_muc:{ten}_sua", args=[doi_tuong.pk]))
            self.assertContains(trang, "data-xem-truoc")
            self.assertContains(trang, "danh_muc/js/quan_ly_anh.js")

    def test_nhan_vien_khong_tai_anh_ajax(self):
        self.client.force_login(self.d.nv)
        url = reverse("danh_muc:anh_tai_len", args=["thuoc", self.d.thuoc.pk])
        self.assertEqual(self.client.post(url, {"cac_anh": [tep_anh()]}, **AJAX).status_code, 403)

    def test_tao_moi_chuyen_sang_trang_sua_de_them_anh(self):
        phan_hoi = self.client.post(
            reverse("danh_muc:chi_nhanh_tao"),
            {
                "ma_chi_nhanh": "CN9",
                "ten_chi_nhanh": "Chi nhánh chín",
                "dia_chi": "TP.HCM",
                "dang_hoat_dong": "on",
                "gio_mo_cua": "07:00",
                "gio_dong_cua": "22:00",
                "kinh_do": "106.7",
                "vi_do": "10.7",
                "gioi_thieu": "<p>Nhà thuốc mới</p>",
            },
        )
        self.assertEqual(phan_hoi.status_code, 302)
        self.assertRegex(phan_hoi["Location"], r"/chi-nhanh/\d+/sua/$")


class AnhTrongNoiDungTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_tai_anh_vao_noi_dung_va_phuc_vu_cong_khai(self):
        self.client.force_login(self.d.admin)
        phan_hoi = self.client.post(
            reverse("danh_muc:anh_noi_dung_tai_len"), {"anh": tep_anh()}, **AJAX
        )
        du_lieu = phan_hoi.json()
        self.assertTrue(du_lieu["ok"])
        self.assertTrue(
            AnhNoiDung.objects.filter(pk=int(du_lieu["url"].strip("/").split("/")[-1])).exists()
        )
        self.client.logout()
        anh = self.client.get(du_lieu["url"])
        self.assertEqual(anh.status_code, 200)
        self.assertEqual(anh["Content-Type"], "image/webp")

    def test_khach_khong_tai_anh_noi_dung(self):
        self.client.force_login(self.d.khach)
        phan_hoi = self.client.post(reverse("danh_muc:anh_noi_dung_tai_len"), {"anh": tep_anh()})
        self.assertEqual(phan_hoi.status_code, 403)

    def test_form_thuoc_co_duong_dan_tai_anh_cho_trinh_soan_thao(self):
        self.client.force_login(self.d.admin)
        trang = self.client.get(reverse("danh_muc:thuoc_sua", args=[self.d.thuoc.pk]))
        self.assertContains(trang, f'data-url-tai-anh="{reverse("danh_muc:anh_noi_dung_tai_len")}"')
        # một khung duy nhất cho phần mô tả dài
        self.assertContains(trang, 'name="noi_dung_chi_tiet"')
        self.assertNotContains(trang, 'name="cong_dung"')


class LamSachNoiDungTests(TestCase):
    def test_giu_dinh_dang_mau_co_chu_va_anh_he_thong(self):
        html = (
            '<h3 class="ql-align-center">Công dụng</h3>'
            '<p>Chữ <span style="color: rgb(230, 0, 0); position: fixed">đỏ</span> '
            '<span class="ql-size-large">lớn</span> H<sub>2</sub>O</p>'
            '<p><img class="anh-nd-trai anh-nd-rong-50 x" src="/anh/noi-dung/7/" alt="Hộp thuốc" '
            'onerror="alert(1)"></p>'
        )
        sach = lam_sach_html(html)
        self.assertIn('<h3 class="ql-align-center">', sach)
        self.assertIn("color:rgb(230, 0, 0)", sach)
        self.assertNotIn("position", sach)
        self.assertIn('class="ql-size-large"', sach)
        self.assertIn("<sub>2</sub>", sach)
        self.assertIn('class="anh-nd-trai anh-nd-rong-50"', sach)
        self.assertIn('src="/anh/noi-dung/7/"', sach)
        self.assertNotIn("onerror", sach)

    def test_chan_anh_ngoai_he_thong_va_ma_doc(self):
        sach = lam_sach_html(
            '<img src="https://evil.example/a.png"><script>x</script><a href="javascript:x()">a</a>'
        )
        self.assertNotIn("evil.example", sach)
        self.assertNotIn("script", sach)
        self.assertNotIn("javascript", sach)
