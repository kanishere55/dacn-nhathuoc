from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ung_dung.kho.models import TonKho
from ung_dung.kho.selectors import lay_ton_kha_dung
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton

from ..models import DonHang, PhanBoPhieuBan, PhieuBan
from ..services.dat_hang import dat_giu
from ..services.don_hang import huy_don, xu_ly_qua_han
from ..services.phieu_ban import ban_tai_quay


class TonVaGiuTests(TestCase):
    def setUp(self):
        self.d = tao_du_lieu()

    def test_fefo_chi_lo_hop_le_han_gan_truoc(self):
        xa = tao_ton(self.d, "XA", ngay=30, luong=10)
        gan = tao_ton(self.d, "GAN", ngay=1, luong=5)
        het_han = tao_ton(self.d, "HET", ngay=-1, luong=50)
        cam = tao_ton(self.d, "CAM", ngay=0, luong=50, duoc_ban=False)
        phieu = ban_tai_quay(self.d.nv, self.d.cn, [{"thuoc": self.d.thuoc, "so_luong": 7}])
        self.assertEqual(
            list(
                PhanBoPhieuBan.objects.filter(chi_tiet_phieu_ban__phieu_ban=phieu)
                .order_by("pk")
                .values_list("ton_kho_id", "so_luong")
            ),
            [(gan.pk, 5), (xa.pk, 2)],
        )
        het_han.refresh_from_db()
        cam.refresh_from_db()
        self.assertEqual((het_han.so_luong, cam.so_luong), (50, 50))

    def test_kha_dung_tru_giu_huy_tra_lai_khong_doi_vat_ly(self):
        ton = tao_ton(self.d, luong=10)
        don = dat_giu(self.d.khach, self.d.cn, [{"thuoc": self.d.thuoc, "so_luong": 6}])
        self.assertEqual(lay_ton_kha_dung().get(pk=ton.pk).kha_dung, 4)
        huy_don(self.d.khach, don)
        self.assertEqual(lay_ton_kha_dung().get(pk=ton.pk).kha_dung, 10)
        ton.refresh_from_db()
        self.assertEqual(ton.so_luong, 10)

    def test_het_han_giu_duoc_loai_ke_ca_tac_vu_chua_chay(self):
        ton = tao_ton(self.d)
        don = dat_giu(self.d.khach, self.d.cn, [{"thuoc": self.d.thuoc, "so_luong": 8}])
        DonHang.objects.filter(pk=don.pk).update(
            thoi_diem_tao=timezone.now() - timedelta(days=2),
            thoi_diem_het_giu=timezone.now() - timedelta(hours=1),
        )
        self.assertEqual(lay_ton_kha_dung().get(pk=ton.pk).kha_dung, 10)
        self.client.force_login(self.d.khach)
        phan_hoi = self.client.get(reverse("ban_hang:khach_don_hang_chi_tiet", args=[don.pk]))
        self.assertContains(phan_hoi, "Đã quá hạn")
        self.assertNotContains(phan_hoi, "Hủy đơn")
        self.assertEqual(xu_ly_qua_han(), 1)
        don.refresh_from_db()
        self.assertEqual(don.trang_thai, "het_han")
        self.assertEqual(xu_ly_qua_han(), 0)

    def test_khong_du_toan_don_rollback_tat_ca(self):
        tao_ton(self.d)
        with self.assertRaises(ValidationError):
            dat_giu(self.d.khach, self.d.cn, [{"thuoc": self.d.thuoc, "so_luong": 100}])
        self.assertEqual(DonHang.objects.count(), 0)

    def test_nhan_giu_khong_chiem_giu_khach_khac_va_khong_tru_hai_lan(self):
        ton = tao_ton(self.d, luong=10)
        mot = dat_giu(self.d.khach, self.d.cn, [{"thuoc": self.d.thuoc, "so_luong": 6}])
        hai = dat_giu(self.d.khac, self.d.cn, [{"thuoc": self.d.thuoc, "so_luong": 4}])
        phieu = ban_tai_quay(self.d.nv, self.d.cn, [], don_hang=mot)
        self.assertEqual(ban_tai_quay(self.d.nv, self.d.cn, [], don_hang=mot).pk, phieu.pk)
        ton.refresh_from_db()
        hai.refresh_from_db()
        self.assertEqual((ton.so_luong, hai.trang_thai), (4, "dang_giu"))
        self.assertEqual(lay_ton_kha_dung().get(pk=ton.pk).kha_dung, 0)

    def test_nhan_vien_khong_ban_chi_nhanh_khac(self):
        ton = tao_ton(self.d, chi_nhanh=self.d.cn2)
        with self.assertRaises(PermissionDenied):
            ban_tai_quay(self.d.nv, self.d.cn2, [{"thuoc": self.d.thuoc, "so_luong": 1}])
        ton.refresh_from_db()
        self.assertEqual(ton.so_luong, 10)

    def test_gui_lai_cung_form_chi_mot_phieu(self):
        ton = tao_ton(self.d)
        for _ in range(2):
            ban_tai_quay(
                self.d.nv,
                self.d.cn,
                [{"thuoc": self.d.thuoc, "so_luong": 2}],
                khoa_yeu_cau="cung-mot-form",
            )
        self.assertEqual(PhieuBan.objects.count(), 1)
        self.assertEqual(TonKho.objects.get(pk=ton.pk).so_luong, 8)
