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
        self.assertEqual(dict(pham_vi["cac_luong"])["VIEN"]["kha_dung"], 17)
        self.assertEqual(lay_bao_cao(d.admin, ngay, ngay)["tong_tien_ban"], 20000)
        self.client.force_login(d.ql)
        self.assertContains(self.client.get(reverse("bao_cao:tong_hop")), "Chứng từ trong kỳ")
        tra_ve = self.client.get(
            reverse("bao_cao:tong_hop"),
            {"tu_ngay": ngay.isoformat(), "den_ngay": ngay.isoformat(), "chi_nhanh": d.cn2.pk},
            headers={"HX-Request": "true"},
        )
        self.assertContains(tra_ve, "Bộ lọc chưa hợp lệ.")
        self.assertNotContains(tra_ve, "<html")

        d.cn2.dang_hoat_dong = False
        d.cn2.save(update_fields=["dang_hoat_dong"])
        self.client.force_login(d.admin)
        tra_ve = self.client.get(
            reverse("bao_cao:tong_hop"),
            {"tu_ngay": ngay.isoformat(), "den_ngay": ngay.isoformat(), "chi_nhanh": d.cn2.pk},
        )
        self.assertContains(tra_ve, "Chứng từ trong kỳ")
        self.assertNotContains(tra_ve, "Bộ lọc chưa hợp lệ.")
        self.assertEqual(lay_bao_cao(d.admin, ngay, ngay, d.cn2)["tong_tien_ban"], 14000)
