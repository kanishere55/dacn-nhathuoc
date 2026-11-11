from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from ung_dung.danh_muc.models import QuyDoiBaoGoi
from ung_dung.kho.models import (
    ChiTietPhieuKiemKe,
    PhieuDieuChuyen,
    PhieuKiemKe,
    PhieuTraNhaCungCap,
    TonKho,
)
from ung_dung.kho.services.phieu_dieu_chuyen import dieu_chuyen
from ung_dung.kho.services.phieu_kiem_ke import kiem_ke
from ung_dung.kho.services.phieu_nhap import nhap_hang
from ung_dung.kho.services.phieu_tra_nha_cung_cap import tra_nha_cung_cap

from .du_lieu import tao_du_lieu, tao_ton


class ChungTuKhoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def nhap_lo(self, luong, quy_doi=None):
        d = self.d
        return nhap_hang(
            d.nv,
            d.cn,
            d.ncc,
            [
                {
                    "thuoc": d.thuoc,
                    "so_luong": luong,
                    "quy_doi_bao_goi": quy_doi,
                    "ma_lo_thuoc": "LO-10",
                    "ngay_het_han": timezone.localdate() + timedelta(days=10),
                    "don_gia": 1000,
                }
            ],
        )

    def test_nhap_quy_doi_va_tra_ncc_khong_chiem_phan_dang_giu(self):
        d = self.d
        quy_doi = QuyDoiBaoGoi.objects.create(thuoc=d.thuoc, ten_quy_doi_bao_goi="Hộp", he_so=10)
        phieu = self.nhap_lo(2, quy_doi)
        ton = TonKho.objects.get(chi_nhanh=d.cn)
        self.assertEqual(ton.so_luong, 20)
        from ung_dung.ban_hang.services.dat_hang import dat_giu

        dat_giu(d.khach, d.cn, [{"thuoc": d.thuoc, "so_luong": 12}])
        dong = {"lo_thuoc": ton.lo_thuoc, "so_luong": 9}
        with self.assertRaises(ValidationError):
            tra_nha_cung_cap(d.ql, phieu, [dong], "Vỉ móp khi nhận")
        self.assertFalse(PhieuTraNhaCungCap.objects.exists())
        dong["so_luong"] = 8
        tra_nha_cung_cap(d.ql, phieu, [dong], "Vỉ móp khi nhận")
        ton.refresh_from_db()
        self.assertEqual(ton.so_luong, 12)

    def test_dieu_chuyen_giu_nguyen_tong_va_kiem_ke_tu_choi_so_du_cu(self):
        d = self.d
        self.nhap_lo(20)
        ton = TonKho.objects.get(chi_nhanh=d.cn)
        dieu_chuyen(d.ql, d.cn, d.cn2, [{"thuoc": d.thuoc, "so_luong": 7}])
        ton.refresh_from_db()
        self.assertEqual(ton.so_luong, 13)
        self.assertEqual(TonKho.objects.get(chi_nhanh=d.cn2, lo_thuoc=ton.lo_thuoc).so_luong, 7)
        dong = {"ton_kho": ton, "so_luong_so_sach": 20, "so_luong_thuc_te": 13}
        with self.assertRaises(ValidationError):
            kiem_ke(d.ql, d.cn, [dong])
        self.assertFalse(PhieuKiemKe.objects.exists())
        dong["so_luong_so_sach"] = 13
        dong["so_luong_thuc_te"] = 12
        kiem_ke(d.ql, d.cn, [dong])
        ton.refresh_from_db()
        self.assertEqual(ton.so_luong, 12)

    def test_form_kiem_ke_chi_ghi_lo_da_dem_va_nhan_gia_tri_khong(self):
        d = self.d
        lo_da_dem = tao_ton(d, ma="LO-DEM")
        lo_bo_trong = tao_ton(d, ma="LO-BO-TRONG")
        self.client.force_login(d.ql)
        url = reverse("kho:phieu_kiem_ke_tao")
        du_lieu = {
            "chi_nhanh": d.cn.pk,
            "da_dem_thuc_te": "on",
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 2,
            "form-0-ton_kho": lo_da_dem.pk,
            "form-0-so_luong_so_sach": 10,
            "form-0-so_luong_thuc_te": "0",
            "form-1-ton_kho": lo_bo_trong.pk,
            "form-1-so_luong_so_sach": 10,
            "form-1-so_luong_thuc_te": "",
        }
        lo_da_dem.so_luong = 9
        lo_da_dem.save(update_fields=["so_luong"])
        self.assertContains(self.client.post(url, du_lieu), "cần xem lại")
        self.assertFalse(PhieuKiemKe.objects.exists())

        du_lieu["form-0-so_luong_so_sach"] = 9
        phan_hoi = self.client.post(url, du_lieu)
        phieu = PhieuKiemKe.objects.get()
        self.assertRedirects(phan_hoi, reverse("kho:phieu_kiem_ke_chi_tiet", args=[phieu.pk]))
        dong = ChiTietPhieuKiemKe.objects.get(phieu_kiem_ke=phieu)
        self.assertEqual(dong.lo_thuoc_id, lo_da_dem.lo_thuoc_id)
        lo_da_dem.refresh_from_db()
        lo_bo_trong.refresh_from_db()
        self.assertEqual((lo_da_dem.so_luong, lo_bo_trong.so_luong), (0, 10))

    def test_form_kiem_ke_khong_truy_van_tung_lo(self):
        d = self.d
        tao_ton(d, ma="LO-01")
        self.client.force_login(d.ql)
        url = reverse("kho:phieu_kiem_ke_tao")
        with CaptureQueriesContext(connection) as mot_lo:
            self.assertContains(self.client.get(url), "LO-01")
        for so in range(2, 56):
            tao_ton(d, ma=f"LO-{so:02d}")
        with CaptureQueriesContext(connection) as nhieu_lo:
            self.assertContains(self.client.get(url), "LO-55")
        self.assertEqual(len(nhieu_lo), len(mot_lo))
        phan_hoi = self.client.get(url, {"q": "LO-55"})
        self.assertContains(phan_hoi, "LO-55")
        self.assertNotContains(phan_hoi, "LO-01")

    def test_so_luong_vuot_gioi_han_bao_loi_chung_khong_500(self):
        from ung_dung.kho.forms import DongKiemKeForm

        self.nhap_lo(1)
        with self.assertRaises(ValidationError) as loi:
            self.nhap_lo(2147483647)
        self.assertFalse(hasattr(loi.exception, "error_dict"))
        self.assertEqual(TonKho.objects.get(chi_nhanh=self.d.cn).so_luong, 1)
        ton = TonKho.objects.get(chi_nhanh=self.d.cn)
        form = DongKiemKeForm(
            data={"ton_kho": ton.pk, "so_luong_so_sach": 1, "so_luong_thuc_te": 2147483648},
            nguoi=self.d.ql,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("so_luong_thuc_te", form.errors)
        self.assertIn("lô LO-10", str(form.fields["ton_kho"].label_from_instance(ton)))

    def test_chi_nhanh_nhan_xem_duoc_phieu_dieu_chuyen_den(self):
        d = self.d
        self.nhap_lo(20)
        phieu = dieu_chuyen(d.ql, d.cn, d.cn2, [{"thuoc": d.thuoc, "so_luong": 2}])
        self.client.force_login(d.ql2)
        self.assertEqual(
            self.client.get(reverse("kho:phieu_dieu_chuyen_chi_tiet", args=[phieu.pk])).status_code,
            200,
        )
        self.assertContains(
            self.client.get(reverse("kho:phieu_dieu_chuyen_danh_sach")), phieu.ma_phieu_dieu_chuyen
        )

    def test_dieu_chuyen_cat_ky_tu_vo_hinh_o_hai_dau_ghi_chu(self):
        self.nhap_lo(20)
        self.client.force_login(self.d.ql)
        phan_hoi = self.client.post(
            reverse("kho:phieu_dieu_chuyen_tao"),
            {
                "chi_nhanh_nguon": self.d.cn.pk,
                "chi_nhanh_dich": self.d.cn2.pk,
                "ghi_chu": "\u200b\ufeffChuyển để bổ sung tồn\u200b",
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-0-thuoc": self.d.thuoc.pk,
                "form-0-so_luong": "7",
            },
        )
        self.assertEqual(phan_hoi.status_code, 302)
        self.assertEqual(PhieuDieuChuyen.objects.get().ghi_chu, "Chuyển để bổ sung tồn")

    def test_tra_nha_cung_cap_bat_buoc_ly_do_ke_ca_khi_chi_co_ky_tu_vo_hinh(self):
        phieu_nhap = self.nhap_lo(20)
        lo_thuoc_id = TonKho.objects.get(chi_nhanh=self.d.cn).lo_thuoc_id
        self.client.force_login(self.d.ql)
        phan_hoi = self.client.post(
            reverse("kho:phieu_tra_tao"),
            {
                "phieu_nhap": phieu_nhap.pk,
                "ghi_chu": "\ufeff\u200b",
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-0-lo_thuoc": lo_thuoc_id,
                "form-0-so_luong": "7",
            },
        )
        self.assertEqual(phan_hoi.status_code, 200)
        self.assertContains(phan_hoi, "Ghi lý do trả")
        # Lô đã chọn vẫn được giữ khi trang báo lỗi thiếu lý do.
        self.assertContains(phan_hoi, f'value="{lo_thuoc_id}" selected')
        self.assertNotContains(phan_hoi, "Lô này không có trong phiếu nhập đã chọn")
        self.assertFalse(PhieuTraNhaCungCap.objects.exists())
        with self.assertRaises(ValidationError):
            tra_nha_cung_cap(
                self.d.ql,
                phieu_nhap,
                [{"lo_thuoc_id": lo_thuoc_id, "so_luong": 7}],
                "﻿​",
            )
