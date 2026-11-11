from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import PhieuDieuChuyen, PhieuKiemKe, PhieuNhap, PhieuTraNhaCungCap, TonKho
from ..services.phieu_dieu_chuyen import dieu_chuyen
from ..services.phieu_kiem_ke import kiem_ke
from ..services.phieu_nhap import nhap_hang
from ..services.phieu_tra_nha_cung_cap import tra_nha_cung_cap
from .du_lieu import tao_du_lieu


class QuyenQuanTriKhoTests(TestCase):
    """Quản trị chuỗi lập được mọi chứng từ kho ở mọi chi nhánh; nhân viên vẫn bị giới hạn."""

    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        cls.dong_nhap = {
            "thuoc": cls.d.thuoc,
            "ma_lo_thuoc": "LO-NHAP",
            "ngay_het_han": timezone.localdate() + timedelta(days=10),
            "so_luong": 20,
            "don_gia": 1000,
        }
        cls.phieu = nhap_hang(cls.d.ql2, cls.d.cn2, cls.d.ncc, [cls.dong_nhap])
        cls.ton = TonKho.objects.get(chi_nhanh=cls.d.cn2)

    def setUp(self):
        self.client.force_login(self.d.admin)

    def test_quan_tri_lap_phieu_nhap_o_chi_nhanh_bat_ky(self):
        d = self.d
        trang = self.client.get(reverse("kho:phieu_nhap_tao"))
        self.assertEqual(trang.status_code, 200)
        nhap_hang(d.admin, d.cn2, d.ncc, [{**self.dong_nhap, "ma_lo_thuoc": "LO-NHAP-2"}])
        self.assertEqual(PhieuNhap.objects.count(), 2)

    def test_quan_tri_dieu_chuyen_tra_ncc_kiem_ke(self):
        d = self.d
        for ten in ("phieu_dieu_chuyen", "phieu_tra", "phieu_kiem_ke", "phieu_xuat_huy"):
            with self.subTest(trang=ten):
                self.assertEqual(self.client.get(reverse(f"kho:{ten}_tao")).status_code, 200)
        dieu_chuyen(d.admin, d.cn2, d.cn, [{"thuoc": d.thuoc, "so_luong": 3}])
        tra_nha_cung_cap(
            d.admin, self.phieu, [{"lo_thuoc": self.ton.lo_thuoc, "so_luong": 2}], "Giao sai lô"
        )
        kiem_ke(
            d.admin,
            d.cn2,
            [{"ton_kho": self.ton, "so_luong_so_sach": 15, "so_luong_thuc_te": 14}],
        )
        self.assertEqual(PhieuDieuChuyen.objects.count(), 1)
        self.assertEqual(PhieuTraNhaCungCap.objects.count(), 1)
        self.assertEqual(PhieuKiemKe.objects.count(), 1)

    def test_quan_tri_thay_nut_tao_tren_moi_danh_sach(self):
        for ten in ("phieu_nhap", "phieu_tra", "phieu_dieu_chuyen", "phieu_kiem_ke"):
            with self.subTest(chung_tu=ten):
                trang = self.client.get(reverse(f"kho:{ten}_danh_sach"))
                self.assertContains(trang, reverse(f"kho:{ten}_tao"))
        ton = self.client.get(reverse("kho:ton_kho_danh_sach"))
        self.assertContains(ton, self.d.cn2.ten_chi_nhanh)

    def test_nhan_vien_khong_dieu_chuyen_va_khong_lap_o_chi_nhanh_khac(self):
        d = self.d
        with self.assertRaises(PermissionDenied):
            dieu_chuyen(d.nv, d.cn, d.cn2, [{"thuoc": d.thuoc, "so_luong": 1}])
        with self.assertRaises(PermissionDenied):
            nhap_hang(d.nv, d.cn2, d.ncc, [self.dong_nhap])

    def test_quan_tri_doi_duoc_trang_thai_lo(self):
        lo = self.ton.lo_thuoc
        url = reverse("kho:lo_thuoc_doi_trang_thai", args=[lo.pk])
        self.assertContains(self.client.get(reverse("kho:lo_thuoc_danh_sach")), url)
        self.assertEqual(
            self.client.post(url, {"duoc_phep_ban": "0", "ly_do": "Nghi lỗi bao bì"}).status_code,
            302,
        )
        lo.refresh_from_db()
        self.assertFalse(lo.duoc_phep_ban)
