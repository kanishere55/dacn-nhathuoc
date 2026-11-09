from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from ung_dung.ban_hang.models import DonHang
from ung_dung.ban_hang.services.dat_hang import dat_giu
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton

from ..models import DanhGiaChiNhanh
from ..services.danh_gia import luu_danh_gia_chi_nhanh


class DanhGiaChiNhanhTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        tao_ton(cls.d, luong=20)
        don = dat_giu(cls.d.khach, cls.d.cn, [{"thuoc": cls.d.thuoc, "so_luong": 1}])
        DonHang.objects.filter(pk=don.pk).update(trang_thai="hoan_thanh")

    def test_chi_khach_co_don_hoan_thanh_tai_chi_nhanh(self):
        d = self.d
        with self.assertRaises(ValidationError):
            luu_danh_gia_chi_nhanh(d.khach, d.cn2, 5)
        with self.assertRaises(ValidationError):
            luu_danh_gia_chi_nhanh(d.khac, d.cn, 5)
        with self.assertRaises(PermissionDenied):
            luu_danh_gia_chi_nhanh(d.nv, d.cn, 5)
        luu_danh_gia_chi_nhanh(d.khach, d.cn, 4, "Tư vấn kỹ​ ")
        luu_danh_gia_chi_nhanh(d.khach, d.cn, 5, "Sửa lại")
        danh_gia = DanhGiaChiNhanh.objects.get()
        self.assertEqual((danh_gia.so_sao, danh_gia.noi_dung_danh_gia), (5, "Sửa lại"))

    def test_trang_chi_nhanh_hien_form_va_quan_tri_an_nhan_xet(self):
        d = self.d
        url = reverse("danh_muc:khach_chi_nhanh_chi_tiet", args=[d.cn.ma_chi_nhanh])
        self.client.force_login(d.khach)
        self.assertContains(self.client.get(url), "Gửi đánh giá")
        self.client.post(
            reverse("danh_muc:khach_danh_gia_chi_nhanh", args=[d.cn.ma_chi_nhanh]),
            {"so_sao": "4", "noi_dung": "Nhân viên nhiệt tình"},
        )
        self.assertContains(self.client.get(url), "Nhân viên nhiệt tình")
        danh_gia = DanhGiaChiNhanh.objects.get()
        self.client.force_login(d.admin)
        self.assertContains(
            self.client.get(reverse("danh_muc:danh_gia_danh_sach") + "?loai=chi_nhanh"),
            "Nhân viên nhiệt tình",
        )
        self.client.post(
            reverse("danh_muc:danh_gia_chi_nhanh_doi_hien_thi", args=[danh_gia.pk]),
            {"next": "https://ngoai.example/"},
        )
        danh_gia.refresh_from_db()
        self.assertFalse(danh_gia.dang_hien_thi)
        self.client.logout()
        self.assertNotContains(self.client.get(url), "Nhân viên nhiệt tình")
