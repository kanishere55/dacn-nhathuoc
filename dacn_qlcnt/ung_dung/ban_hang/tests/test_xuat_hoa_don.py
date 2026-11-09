from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton
from ung_dung.thong_bao.models import NhatKyEmail

from ..models import DonHang, YeuCauXuatHoaDon
from ..services.dat_hang import dat_giu
from ..services.xuat_hoa_don import gui_yeu_cau_xuat_hoa_don, xu_ly_yeu_cau_xuat_hoa_don

CONG_TY = {
    "ten_cong_ty": "Công ty TNHH Dược Thử Nghiệm",
    "ma_so_thue": "0312345678",
    "dia_chi_cong_ty": "12 Nguyễn Huệ, Quận 1, TP.HCM",
    "email_nhan_hoa_don": "KeToan@CongTy.vn",
}


class XuatHoaDonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        tao_ton(cls.d, luong=20)
        cls.don = dat_giu(cls.d.khach, cls.d.cn, [{"thuoc": cls.d.thuoc, "so_luong": 1}])

    def hoan_thanh(self):
        DonHang.objects.filter(pk=self.don.pk).update(trang_thai="hoan_thanh")

    def test_chi_chu_don_da_hoan_thanh_moi_gui_mot_lan(self):
        with self.assertRaises(ValidationError):
            gui_yeu_cau_xuat_hoa_don(self.d.khach, self.don, CONG_TY)
        self.hoan_thanh()
        with self.assertRaises(PermissionDenied):
            gui_yeu_cau_xuat_hoa_don(self.d.khac, self.don, CONG_TY)
        yeu_cau = gui_yeu_cau_xuat_hoa_don(self.d.khach, self.don, CONG_TY)
        self.assertEqual(yeu_cau.email_nhan_hoa_don, "ketoan@congty.vn")
        with self.assertRaises(ValidationError):
            gui_yeu_cau_xuat_hoa_don(self.d.khach, self.don, CONG_TY)

    def test_nhan_vien_dung_chi_nhanh_xu_ly_va_email_bao_khach(self):
        self.hoan_thanh()
        yeu_cau = gui_yeu_cau_xuat_hoa_don(self.d.khach, self.don, CONG_TY)
        with self.assertRaises(PermissionDenied):
            xu_ly_yeu_cau_xuat_hoa_don(self.d.ql2, yeu_cau, "da_xuat", "Số 0000001")
        with self.assertRaises(ValidationError):
            xu_ly_yeu_cau_xuat_hoa_don(self.d.nv, yeu_cau, "da_xuat", "  ")
        with self.captureOnCommitCallbacks(execute=True):
            xu_ly_yeu_cau_xuat_hoa_don(self.d.nv, yeu_cau, "da_xuat", "Ký hiệu 1C26TAA, số 0000001")
        yeu_cau.refresh_from_db()
        self.assertEqual((yeu_cau.trang_thai, yeu_cau.nguoi_xu_ly), ("da_xuat", self.d.nv))
        self.assertTrue(NhatKyEmail.objects.filter(loai_email="xuat_hoa_don").exists())
        self.assertEqual(mail.outbox[-1].to, ["ketoan@congty.vn"])
        with self.assertRaises(ValidationError):
            xu_ly_yeu_cau_xuat_hoa_don(self.d.nv, yeu_cau, "tu_choi", "Sai mã số thuế")

    def test_form_khach_va_trang_nhan_vien(self):
        self.hoan_thanh()
        self.client.force_login(self.d.khach)
        url_don = reverse("ban_hang:khach_don_hang_chi_tiet", args=[self.don.pk])
        self.assertContains(self.client.get(url_don), "Cần hóa đơn đứng tên doanh nghiệp?")
        sai = self.client.post(
            reverse("ban_hang:khach_hoa_don_cong_ty", args=[self.don.pk]),
            {**CONG_TY, "ma_so_thue": "12345"},
        )
        self.assertContains(sai, "Mã số thuế gồm 10 chữ số")
        self.client.post(reverse("ban_hang:khach_hoa_don_cong_ty", args=[self.don.pk]), CONG_TY)
        self.assertEqual(YeuCauXuatHoaDon.objects.count(), 1)
        self.client.force_login(self.d.nv)
        trang = self.client.get(reverse("ban_hang:xuat_hoa_don_danh_sach"))
        self.assertContains(trang, "0312345678")
        self.client.force_login(self.d.ql2)
        trang = self.client.get(reverse("ban_hang:xuat_hoa_don_danh_sach"))
        self.assertNotContains(trang, "0312345678")
