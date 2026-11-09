from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ung_dung.kho.tests.du_lieu import tao_du_lieu

from ..models import TinTuc


class TinTucTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def tao_tin(self, **them):
        return TinTuc.objects.create(
            **{
                "duong_dan_tin_tuc": "phong-cum",
                "tieu_de": "Phòng cúm mùa mưa",
                "tom_tat": "Năm việc nên làm để phòng cúm.",
                "noi_dung_tin_tuc": "<p>Rửa tay thường xuyên.</p>",
                "nguoi_viet": self.d.admin,
                **them,
            }
        )

    def test_khach_chi_thay_tin_dang_hien_va_den_gio(self):
        self.tao_tin()
        self.tao_tin(
            duong_dan_tin_tuc="hen-gio",
            tieu_de="Bài hẹn giờ",
            thoi_diem_dang=timezone.now() + timedelta(days=1),
        )
        self.tao_tin(duong_dan_tin_tuc="da-an", tieu_de="Bài đã ẩn", dang_hien_thi=False)
        danh_sach = self.client.get(reverse("noi_dung:khach_tin_tuc_danh_sach"))
        self.assertContains(danh_sach, "Phòng cúm mùa mưa")
        self.assertNotContains(danh_sach, "Bài hẹn giờ")
        self.assertNotContains(danh_sach, "Bài đã ẩn")
        url = reverse("noi_dung:khach_tin_tuc_chi_tiet", args=["phong-cum"])
        self.assertContains(self.client.get(url), "Rửa tay thường xuyên")
        an = reverse("noi_dung:khach_tin_tuc_chi_tiet", args=["hen-gio"])
        self.assertEqual(self.client.get(an).status_code, 404)

    def test_quan_tri_viet_tin_va_noi_dung_duoc_lam_sach(self):
        self.client.force_login(self.d.admin)
        phan_hoi = self.client.post(
            reverse("noi_dung:tin_tuc_tao"),
            {
                "tieu_de": "  Uống thuốc đúng giờ ",
                "duong_dan_tin_tuc": "uong-thuoc-dung-gio",
                "tom_tat": "Vì sao cần uống kháng sinh đủ liều.",
                "noi_dung_tin_tuc": "<p>Đủ liều</p><script>alert(1)</script>",
                "thoi_diem_dang": "",
                "dang_hien_thi": "on",
            },
        )
        self.assertRedirects(phan_hoi, reverse("noi_dung:tin_tuc_danh_sach"))
        tin = TinTuc.objects.get()
        self.assertEqual((tin.tieu_de, tin.nguoi_viet), ("Uống thuốc đúng giờ", self.d.admin))
        self.assertNotIn("script", tin.noi_dung_tin_tuc)
        self.assertLessEqual(tin.thoi_diem_dang, timezone.now())

    def test_nhan_su_chi_nhanh_khong_quan_ly_tin(self):
        self.client.force_login(self.d.ql)
        self.assertEqual(self.client.get(reverse("noi_dung:tin_tuc_danh_sach")).status_code, 403)
