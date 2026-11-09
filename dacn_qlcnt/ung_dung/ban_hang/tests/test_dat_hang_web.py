"""Luồng mua hàng qua giao diện: giỏ → đặt hàng → xử lý đơn."""

from unittest import mock

from django.contrib.gis.geos import Point
from django.test import TestCase, override_settings
from django.urls import reverse

from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton
from ung_dung.tai_khoan.models import DiaChiGiaoHang
from ung_dung.thanh_toan.models import GiaoDichThanhToan

from ..models import DonHang, LichSuDonHang, PhieuBan

DUONG_DI = "ung_dung.ban_hang.services.giao_hang.khoang_cach_duong_di"


def quang_duong(met):
    return lambda den, cac_diem, cac_thang: [(met, False) for _ in cac_diem]


class DatHangWebTests(TestCase):
    def setUp(self):
        self.d = tao_du_lieu()
        tao_ton(self.d, luong=30)
        self.client.force_login(self.d.khach)
        self.dia_chi = DiaChiGiaoHang.objects.create(
            tai_khoan=self.d.khach,
            ten_nguoi_nhan="Nguyễn Văn A",
            so_dien_thoai="0901234567",
            dia_chi="12 Nguyễn Huệ, Quận 1",
            vi_tri=Point(106.702, 10.772, srid=4326),
        )

    def them_gio(self, so_luong=2):
        return self.client.post(
            reverse("ban_hang:gio_hang_them", args=[self.d.thuoc.ma_thuoc]),
            {"so_luong": so_luong},
        )

    def test_gio_hang_them_sua_xoa(self):
        self.them_gio(2)
        self.them_gio(3)
        phan_hoi = self.client.get(reverse("ban_hang:gio_hang"))
        self.assertContains(phan_hoi, self.d.thuoc.ten_thuoc)
        self.assertContains(phan_hoi, "10.000 đ")
        self.client.post(reverse("ban_hang:gio_hang_sua", args=[self.d.thuoc.pk]), {"so_luong": 1})
        self.assertContains(self.client.get(reverse("ban_hang:gio_hang")), "2.000 đ")
        self.client.post(reverse("ban_hang:gio_hang_sua", args=[self.d.thuoc.pk]), {"so_luong": 0})
        self.assertNotContains(self.client.get(reverse("ban_hang:gio_hang")), "2.000 đ")

    @mock.patch(DUONG_DI, side_effect=quang_duong(4200))
    def test_giao_hang_cod_tinh_phi_va_tao_don(self, _):
        self.them_gio(2)
        phan_hoi = self.client.get(reverse("ban_hang:dat_hang"), {"hinh_thuc_nhan": "giao_hang"})
        self.assertContains(phan_hoi, "25.000 đ")  # 15.000 + 2 km × 5.000
        phan_hoi = self.client.post(
            reverse("ban_hang:dat_hang"),
            {
                "hinh_thuc_nhan": "giao_hang",
                "dia_chi": self.dia_chi.pk,
                "chi_nhanh": self.d.cn.pk,
                "phuong_thuc_thanh_toan": "cod",
            },
        )
        don = DonHang.objects.get()
        self.assertRedirects(phan_hoi, reverse("ban_hang:khach_don_hang_chi_tiet", args=[don.pk]))
        self.assertEqual(
            (don.trang_thai, don.tien_hang, don.phi_giao_hang, don.tong_thanh_toan),
            ("cho_xac_nhan", 4000, 25000, 29000),
        )
        self.assertEqual(don.dia_chi_giao, "12 Nguyễn Huệ, Quận 1")
        self.assertFalse(self.client.session.get("gio_hang"))
        # Bấm đặt lần nữa với giỏ đã trống không tạo đơn thứ hai.
        self.client.post(reverse("ban_hang:dat_hang"), {"hinh_thuc_nhan": "giao_hang"})
        self.assertEqual(DonHang.objects.count(), 1)

    @mock.patch(DUONG_DI, side_effect=quang_duong(16_000))
    def test_ngoai_ban_kinh_khong_dat_duoc(self, _):
        self.them_gio(1)
        phan_hoi = self.client.post(
            reverse("ban_hang:dat_hang"),
            {"hinh_thuc_nhan": "giao_hang", "phuong_thuc_thanh_toan": "cod"},
        )
        self.assertEqual(phan_hoi.status_code, 200)
        self.assertFalse(DonHang.objects.exists())

    @override_settings(NGAN_HANG_BIN="970436", SO_TAI_KHOAN="0123456789", TEN_TAI_KHOAN="NT")
    @mock.patch(DUONG_DI, side_effect=quang_duong(2000))
    def test_chuyen_khoan_chuyen_sang_trang_thanh_toan(self, _):
        self.them_gio(1)
        phan_hoi = self.client.post(
            reverse("ban_hang:dat_hang"),
            {"hinh_thuc_nhan": "giao_hang", "phuong_thuc_thanh_toan": "chuyen_khoan"},
        )
        don = DonHang.objects.get()
        self.assertRedirects(phan_hoi, reverse("thanh_toan:trang_thanh_toan", args=[don.pk]))
        self.assertContains(
            self.client.get(reverse("ban_hang:khach_don_hang_chi_tiet", args=[don.pk])),
            "Thanh toán ngay",
        )

    def test_thuoc_ke_don_chi_nhan_tai_quay_va_ghi_don_thuoc(self):
        self.d.thuoc.la_thuoc_ke_don = True
        self.d.thuoc.save()
        self.them_gio(1)
        phan_hoi = self.client.get(reverse("ban_hang:dat_hang"), {"hinh_thuc_nhan": "giao_hang"})
        self.assertContains(phan_hoi, "kê đơn")
        self.client.post(
            reverse("ban_hang:dat_hang"),
            {"hinh_thuc_nhan": "giao_hang", "chi_nhanh": self.d.cn.pk},
        )
        don = DonHang.objects.get()
        self.assertEqual((don.hinh_thuc_nhan, don.trang_thai), ("nhan_tai_quay", "dang_giu"))

        self.client.force_login(self.d.nv)
        url = reverse("ban_hang:don_hang_xu_ly", args=[don.pk, "nhan_tai_quay"])
        trang = self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[don.pk]))
        self.assertContains(trang, "Bác sĩ kê đơn")
        self.client.post(url, {"da_kiem_tra_don_thuoc": "on"})
        self.assertFalse(PhieuBan.objects.exists())
        self.client.post(
            url,
            {
                "da_kiem_tra_don_thuoc": "on",
                "ten_nguoi_ke_don": "BS. Lê Minh",
                "noi_kham_benh": "Bệnh viện Nhân dân 115",
                "phuong_thuc_thanh_toan": "chuyen_khoan",
            },
        )
        phieu = PhieuBan.objects.get()
        don.refresh_from_db()
        self.assertEqual(
            (don.trang_thai, don.trang_thai_thanh_toan), ("hoan_thanh", "da_thanh_toan")
        )
        self.assertEqual(phieu.noi_kham_benh, "Bệnh viện Nhân dân 115")
        self.assertEqual(GiaoDichThanhToan.objects.get(phieu_ban=phieu).phuong_thuc, "chuyen_khoan")

    def test_khach_huy_don_dang_giu_va_lich_su(self):
        self.them_gio(1)
        self.client.post(
            reverse("ban_hang:dat_hang"),
            {"hinh_thuc_nhan": "nhan_tai_quay", "chi_nhanh": self.d.cn.pk},
        )
        don = DonHang.objects.get()
        self.client.force_login(self.d.khac)
        self.client.post(reverse("ban_hang:khach_don_hang_huy", args=[don.pk]))
        don.refresh_from_db()
        self.assertEqual(don.trang_thai, "dang_giu")
        self.client.force_login(self.d.khach)
        self.client.post(reverse("ban_hang:khach_don_hang_huy", args=[don.pk]))
        don.refresh_from_db()
        self.assertEqual(don.trang_thai, "da_huy")
        self.assertEqual(
            list(
                LichSuDonHang.objects.filter(don_hang=don).values_list("den_trang_thai", flat=True)
            ),
            ["dang_giu", "da_huy"],
        )

    @mock.patch(DUONG_DI, side_effect=quang_duong(2500))
    def test_nhan_vien_xu_ly_tron_vong_giao_hang(self, _):
        self.them_gio(2)
        self.client.post(
            reverse("ban_hang:dat_hang"),
            {"hinh_thuc_nhan": "giao_hang", "phuong_thuc_thanh_toan": "cod"},
        )
        don = DonHang.objects.get()
        self.client.force_login(self.d.nv)
        for hanh_dong, trang_thai in (
            ("xac_nhan", "dang_chuan_bi"),
            ("giao_van_chuyen", "dang_giao"),
            ("da_giao", "hoan_thanh"),
        ):
            self.client.post(reverse("ban_hang:don_hang_xu_ly", args=[don.pk, hanh_dong]))
            don.refresh_from_db()
            self.assertEqual(don.trang_thai, trang_thai)
        self.assertEqual(don.trang_thai_thanh_toan, "da_thanh_toan")
        # Nhân viên chi nhánh khác không thấy đơn.
        self.client.force_login(self.d.ql2)
        self.assertEqual(
            self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[don.pk])).status_code, 404
        )
