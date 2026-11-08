from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ung_dung.danh_muc.models import ChiNhanh, NhaCungCap, NhanVien, Thuoc
from ung_dung.kho.models import ChiTietPhieuNhap, PhieuNhap, TonKho


class DuLieuMoPhongTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.quan_tri = get_user_model().objects.create_superuser("quan_tri_mo_phong")

    def chay_lenh(self, *co):
        call_command(
            "tao_du_lieu_mo_phong",
            "--quan-tri",
            self.quan_tri.ten_dang_nhap,
            *co,
            stdout=StringIO(),
        )

    def test_moi_chi_nhanh_co_du_nhan_su_va_quan_ly_lap_phieu_nhap(self):
        self.chay_lenh()
        cac_chi_nhanh = list(ChiNhanh.objects.order_by("ma_chi_nhanh"))
        self.assertEqual(len(cac_chi_nhanh), 3)
        self.assertEqual(
            list(Thuoc.objects.order_by("ma_thuoc").values_list("gia_ban", flat=True)),
            [12000, 2000, 5000, 14000, 9000, 6000, 3000, 15000],
        )
        self.assertEqual(PhieuNhap.objects.count(), 3)
        self.assertEqual(NhanVien.objects.count(), 6)
        self.assertEqual(get_user_model().objects.count(), 7)
        for chi_nhanh, tong in zip(cac_chi_nhanh, (689, 651, 850), strict=True):
            with self.subTest(chi_nhanh=chi_nhanh.ma_chi_nhanh):
                cac_tai_khoan = list(get_user_model().objects.filter(chi_nhanh=chi_nhanh))
                self.assertCountEqual(
                    [tai_khoan.vai_tro for tai_khoan in cac_tai_khoan],
                    ["quan_ly_chi_nhanh", "nhan_vien"],
                )
                self.assertEqual(NhanVien.objects.filter(tai_khoan__in=cac_tai_khoan).count(), 2)
                self.assertTrue(
                    all(not tai_khoan.has_usable_password() for tai_khoan in cac_tai_khoan)
                )
                phieu = PhieuNhap.objects.get(chi_nhanh=chi_nhanh)
                self.assertEqual(phieu.nguoi_lap.chi_nhanh_id, chi_nhanh.pk)
                self.assertEqual(phieu.nguoi_lap.vai_tro, "quan_ly_chi_nhanh")
                luong_nhap = dict(
                    ChiTietPhieuNhap.objects.filter(phieu_nhap=phieu).values_list(
                        "lo_thuoc_id", "so_luong"
                    )
                )
                ton_kho = dict(
                    TonKho.objects.filter(chi_nhanh=chi_nhanh).values_list(
                        "lo_thuoc_id", "so_luong"
                    )
                )
                self.assertEqual(len(luong_nhap), 16)
                self.assertEqual(sum(luong_nhap.values()), tong)
                self.assertEqual(ton_kho, luong_nhap)

        with self.assertRaisesMessage(CommandError, "Đã có chi nhánh mô phỏng"):
            self.chay_lenh()
        self.assertEqual(ChiNhanh.objects.count(), 3)
        self.assertEqual(get_user_model().objects.count(), 7)
        self.assertEqual(PhieuNhap.objects.count(), 3)
        self.assertEqual(ChiTietPhieuNhap.objects.count(), 48)
        self.assertEqual(TonKho.objects.count(), 48)

    def test_tuy_chon_kem_tai_khoan_tao_khach_va_dat_mat_khau(self):
        mat_khau = "Thu-mo-phong!2026"
        with patch(
            "ung_dung.kho.management.commands.tao_du_lieu_mo_phong.getpass", return_value=mat_khau
        ) as nhap_mat_khau:
            self.chay_lenh("--kem-tai-khoan")
        nhap_mat_khau.assert_called_once()
        cac_tai_khoan = list(get_user_model().objects.filter(ten_dang_nhap__startswith="mp_"))
        self.assertCountEqual(
            [tai_khoan.ten_dang_nhap for tai_khoan in cac_tai_khoan],
            [
                "mp_khach",
                "mp_quan_ly",
                "mp_nhan_vien",
                "mp_quan_ly_02",
                "mp_nhan_vien_02",
                "mp_quan_ly_03",
                "mp_nhan_vien_03",
            ],
        )
        self.assertTrue(all(tai_khoan.check_password(mat_khau) for tai_khoan in cac_tai_khoan))

    def test_tu_choi_ten_tai_khoan_trung_truoc_khi_ghi_du_lieu(self):
        get_user_model().objects.create_user("mp_nhan_vien_03")
        with self.assertRaisesMessage(CommandError, "Tên tài khoản mô phỏng đã được sử dụng"):
            self.chay_lenh()
        self.assertFalse(NhaCungCap.objects.exists())
        self.assertFalse(ChiNhanh.objects.exists())
        self.assertFalse(PhieuNhap.objects.exists())
        self.assertEqual(get_user_model().objects.count(), 2)
