from datetime import date, timedelta
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ung_dung.ban_hang.models import DonHang
from ung_dung.ban_hang.services.dat_hang import dat_giu
from ung_dung.du_bao.models import DuBaoBayNgay, KetQuaMoHinh, LanThucNghiem, NguonDuLieu
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton
from ung_dung.tro_chuyen.services import ghi_tin_nhan, mo_phong


class BangDieuKhienTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = d = tao_du_lieu()
        tao_ton(d, "LO-CN1", ngay=1, luong=6)
        tao_ton(d, "LO-CN2", ngay=2, luong=20, chi_nhanh=d.cn2)
        nhu_cau = [{"thuoc": d.thuoc, "so_luong": 2}]
        cls.don_mot = dat_giu(d.khach, d.cn, nhu_cau)
        cls.don_hai = dat_giu(d.khach, d.cn2, nhu_cau)
        cls.don_het_han = dat_giu(d.khac, d.cn, nhu_cau)
        DonHang.objects.filter(pk=cls.don_het_han.pk).update(
            thoi_diem_tao=timezone.now() - timedelta(days=2),
            thoi_diem_het_giu=timezone.now() - timedelta(hours=1),
        )

        cls.phong_moi = mo_phong(d.khach, d.cn)
        ghi_tin_nhan(d.khach, cls.phong_moi, str(uuid4()), "Tin đang chờ ở chi nhánh một")
        phong_da_tra_loi = mo_phong(d.khac, d.cn)
        ghi_tin_nhan(d.khac, phong_da_tra_loi, str(uuid4()), "Câu hỏi đã trả lời")
        ghi_tin_nhan(d.nv, phong_da_tra_loi, str(uuid4()), "Đã phản hồi")
        phong_khac = mo_phong(d.khach, d.cn2)
        ghi_tin_nhan(d.khach, phong_khac, str(uuid4()), "Tin riêng ở chi nhánh hai")

        nguon = NguonDuLieu.objects.create(
            ten_nguon_du_lieu="Nguồn thử dashboard", bam_sha256="a" * 64, don_vi_nguon="Đơn vị thử"
        )
        lan = LanThucNghiem.objects.create(
            nguon_du_lieu=nguon,
            ngay_chot_huan_luyen=date(2019, 7, 31),
            ngay_chot_xac_thuc=date(2019, 9, 30),
            ngay_chot_kiem_thu=date(2019, 12, 31),
            cau_hinh={},
        )
        ket_qua = KetQuaMoHinh.objects.create(
            lan_thuc_nghiem=lan,
            ma_atc_nguon="N02BE",
            mo_hinh="sarimax",
            mae_xac_thuc=2.5,
            rmse_xac_thuc=3.0,
            mae_kiem_thu=4.1,
            rmse_kiem_thu=5.0,
            duoc_chon=True,
        )
        DuBaoBayNgay.objects.create(
            ket_qua_mo_hinh=ket_qua,
            ngay_goc=date(2019, 12, 31),
            ky_danh_gia="tuong_lai",
            so_luong_du_bao=15.5,
        )

    def test_quan_tri_co_so_lieu_toan_chuoi_ban_do_nhiet_va_tom_tat_du_bao(self):
        self.client.force_login(self.d.admin)
        trang = self.client.get(reverse("chung:bang_dieu_khien"))
        self.assertContains(trang, "Tổng quan quản trị chuỗi")
        self.assertContains(trang, 'id="ban-do-nhiet"')
        self.assertContains(trang, "data-ban-do-nhiet")
        self.assertContains(trang, reverse("webgis:du_lieu_nhiet"))
        self.assertContains(trang, f'value="{self.d.nhom.pk}" selected>{self.d.nhom.ma_nhom_atc}')
        self.assertContains(trang, "Nguồn thử dashboard")
        self.assertContains(trang, "sarimax")
        self.assertContains(trang, "RMSE kiểm thử")
        self.assertContains(trang, reverse("du_bao:ket_qua") + "#kich-ban")
        self.assertContains(self.client.get(reverse("du_bao:ket_qua")), 'id="kich-ban"')
        self.assertEqual(trang.context["so_chi_nhanh"], 2)
        self.assertEqual(trang.context["so_don_cho_nhan"], 2)
        self.assertEqual(trang.context["so_lo_canh_bao"], 2)
        self.assertEqual(trang.context["so_canh_bao_ton_thap"], 1)
        self.assertContains(trang, self.don_mot.ma_don_hang)
        self.assertContains(trang, self.don_hai.ma_don_hang)
        self.assertNotContains(trang, self.don_het_han.ma_don_hang)
        # quản trị chuỗi có toàn quyền nên cũng bán được tại quầy
        self.assertContains(trang, reverse("ban_hang:phieu_ban_tao"))
        self.assertNotContains(trang, "Tin đang chờ ở chi nhánh một")

    def test_nhan_su_chi_thay_canh_bao_don_va_tin_cua_chi_nhanh_minh(self):
        for nguoi, tieu_de in (
            (self.d.ql, "Tổng quan quản lý chi nhánh"),
            (self.d.nv, "Tổng quan nhân viên"),
        ):
            with self.subTest(vai_tro=nguoi.vai_tro):
                self.client.force_login(nguoi)
                trang = self.client.get(reverse("chung:bang_dieu_khien"))
                self.assertContains(trang, tieu_de)
                self.assertContains(trang, self.d.cn.ten_chi_nhanh)
                self.assertContains(trang, "LO-CN1")
                self.assertContains(trang, self.don_mot.ma_don_hang)
                self.assertContains(trang, "Tin đang chờ ở chi nhánh một")
                self.assertContains(trang, reverse("tro_chuyen:chi_tiet", args=[self.phong_moi.pk]))
                self.assertNotContains(trang, "LO-CN2")
                self.assertNotContains(trang, self.don_hai.ma_don_hang)
                self.assertNotContains(trang, self.don_het_han.ma_don_hang)
                self.assertNotContains(trang, "Tin riêng ở chi nhánh hai")
                self.assertNotContains(trang, "Câu hỏi đã trả lời")
                self.assertNotContains(trang, 'id="ban-do-nhiet"')
                self.assertNotContains(trang, "Nguồn thử dashboard")
                self.assertEqual(trang.context["so_cuoc_co_tin_moi"], 1)
                self.assertEqual(trang.context["so_don_cho_nhan"], 1)
                self.assertEqual(trang.context["so_lo_canh_bao"], 1)
                self.assertEqual(trang.context["so_canh_bao_ton_thap"], 1)
                if nguoi == self.d.ql:
                    self.assertContains(trang, "Xem báo cáo")
                else:
                    self.assertNotContains(trang, "Xem báo cáo")

        self.client.force_login(self.d.ql2)
        trang = self.client.get(reverse("chung:bang_dieu_khien"))
        self.assertContains(trang, "LO-CN2")
        self.assertContains(trang, self.don_hai.ma_don_hang)
        self.assertContains(trang, "Tin riêng ở chi nhánh hai")
        self.assertEqual(trang.context["so_canh_bao_ton_thap"], 0)
        self.assertNotContains(trang, "LO-CN1")
        self.assertNotContains(trang, self.don_mot.ma_don_hang)
