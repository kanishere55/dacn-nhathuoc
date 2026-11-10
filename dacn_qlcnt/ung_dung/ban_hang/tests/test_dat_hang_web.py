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

    def test_cap_nhat_lua_chon_chi_tra_khoi_va_khong_tao_don(self):
        self.them_gio()
        url = reverse("ban_hang:dat_hang")
        lua_chon = {"hinh_thuc_nhan": "nhan_tai_quay", "chi_nhanh": self.d.cn.pk}
        phan_hoi = self.client.get(url, lua_chon, headers={"HX-Request": "true"})
        self.assertEqual(phan_hoi.headers["X-Khoi-Dat-Hang"], "lua-chon")
        self.assertIn("HX-Request", phan_hoi.headers["Vary"])
        self.assertContains(phan_hoi, 'id="lua-chon-dat-hang"')
        self.assertContains(phan_hoi, "Chi nhánh nhận hàng")
        self.assertNotContains(phan_hoi, 'id="form-dat-hang"')
        self.assertNotContains(phan_hoi, "Phí giao hàng")

        phan_hoi = self.client.post(url, {**lua_chon, "cap_nhat": "1", "ghi_chu_khach": "Lời nhắn"})
        self.assertContains(phan_hoi, 'id="form-dat-hang"')
        self.assertContains(phan_hoi, 'value="Lời nhắn"')
        self.assertFalse(DonHang.objects.exists())

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
        # POST cố giao thuốc kê đơn không bị tự đổi thành đơn giữ; khách phải xác nhận lại.
        phan_hoi = self.client.post(
            reverse("ban_hang:dat_hang"),
            {"hinh_thuc_nhan": "giao_hang", "chi_nhanh": self.d.cn.pk},
        )
        self.assertContains(phan_hoi, "chỉ nhận được tại nhà thuốc")
        self.assertFalse(DonHang.objects.exists())
        self.client.post(
            reverse("ban_hang:dat_hang"),
            {"hinh_thuc_nhan": "nhan_tai_quay", "chi_nhanh": self.d.cn.pk},
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

    def test_chi_nhanh_khong_hop_le_khong_tu_doi_khi_dat(self):
        self.them_gio(1)
        phan_hoi = self.client.post(
            reverse("ban_hang:dat_hang"),
            {"hinh_thuc_nhan": "nhan_tai_quay", "chi_nhanh": 999999999},
        )
        self.assertContains(phan_hoi, "Chi nhánh đã chọn không còn đáp ứng")
        self.assertFalse(DonHang.objects.exists())

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
        ):
            self.client.post(reverse("ban_hang:don_hang_xu_ly", args=[don.pk, hanh_dong]))
            don.refresh_from_db()
            self.assertEqual(don.trang_thai, trang_thai)
        # Nhân viên không tự đánh dấu khách đã nhận; chỉ khách xác nhận.
        self.client.post(reverse("ban_hang:don_hang_xu_ly", args=[don.pk, "da_giao"]))
        don.refresh_from_db()
        self.assertEqual(don.trang_thai, "dang_giao")
        trang = self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[don.pk]))
        self.assertContains(trang, "hệ thống tự hoàn thành lúc")
        self.client.force_login(self.d.khach)
        trang = self.client.get(reverse("ban_hang:khach_don_hang_chi_tiet", args=[don.pk]))
        self.assertContains(trang, "Đã nhận được hàng")
        self.client.post(reverse("ban_hang:khach_don_hang_da_nhan", args=[don.pk]))
        don.refresh_from_db()
        self.assertEqual(don.trang_thai, "hoan_thanh")
        self.assertEqual(don.trang_thai_thanh_toan, "da_thanh_toan")
        # Nhân viên chi nhánh khác không thấy đơn.
        self.client.force_login(self.d.ql2)
        self.assertEqual(
            self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[don.pk])).status_code, 404
        )


class HoaDonTests(TestCase):
    def setUp(self):
        self.d = tao_du_lieu()
        self.d.khach.email = "khach@example.com"
        self.d.khach.save()
        tao_ton(self.d, "L01", ngay=40, luong=3)
        tao_ton(self.d, "L02", ngay=200, luong=30)

    @mock.patch(DUONG_DI, side_effect=quang_duong(1500))
    def test_hoa_don_don_giao_hang_cod(self, _):
        from django.core import mail

        from ..hoa_don import du_lieu_hoa_don, ve_pdf
        from ..services.dat_hang import dat_hang
        from ..services.don_hang import giao_cho_van_chuyen, xac_nhan_da_giao, xac_nhan_don

        don = dat_hang(
            self.d.khach,
            self.d.cn,
            [{"thuoc": self.d.thuoc, "so_luong": 5}],
            hinh_thuc_nhan="giao_hang",
            phuong_thuc_thanh_toan="cod",
            giao={
                "ten_nguoi_nhan": "Lê Hoa",
                "so_dien_thoai": "0907654321",
                "dia_chi": "9 Pasteur, Quận 1",
                "vi_tri": Point(106.70, 10.775, srid=4326),
                "khoang_cach_met": 1500,
            },
        )
        phieu = xac_nhan_don(self.d.nv, don)
        hd = du_lieu_hoa_don(phieu)
        self.assertEqual(
            [(lo["ma"], lo["so_luong"]) for lo in hd["cac_dong"][0]["cac_lo"]],
            [("L01", 3), ("L02", 2)],
        )
        self.assertEqual(hd["tong"]["tong"], 25000)
        self.assertEqual(hd["bang_chu"], "Hai mươi lăm nghìn đồng")
        self.assertEqual(hd["con_phai_thu"], 25000)
        self.assertTrue(ve_pdf(hd).startswith(b"%PDF"))

        self.client.force_login(self.d.khach)
        url = reverse("ban_hang:khach_hoa_don_in", args=[don.pk])
        self.assertEqual(self.client.get(url).status_code, 404)  # chưa hoàn thành
        giao_cho_van_chuyen(self.d.nv, don)
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            xac_nhan_da_giao(self.d.khach, don)
        self.assertEqual(mail.outbox[-1].attachments[0][2], "application/pdf")
        phan_hoi = self.client.get(url)
        self.assertContains(phan_hoi, "Hai mươi lăm nghìn đồng")
        self.assertContains(phan_hoi, "Lô L01")
        pdf = self.client.get(reverse("ban_hang:khach_hoa_don_pdf", args=[don.pk]) + "?tai=1")
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertIn("attachment", pdf["Content-Disposition"])
        self.client.force_login(self.d.khac)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_hoa_don_ban_tai_quay_cho_nhan_vien(self):
        from ..services.phieu_ban import ban_tai_quay

        phieu = ban_tai_quay(self.d.nv, self.d.cn, [{"thuoc": self.d.thuoc, "so_luong": 2}])
        self.client.force_login(self.d.nv)
        for ten in ("ban_hang:phieu_ban_chi_tiet", "ban_hang:phieu_ban_in"):
            phan_hoi = self.client.get(reverse(ten, args=[phieu.pk]))
            self.assertContains(phan_hoi, "Khách mua tại quầy")
            self.assertContains(phan_hoi, "Bốn nghìn đồng")
        self.client.force_login(self.d.ql2)
        self.assertEqual(
            self.client.get(reverse("ban_hang:phieu_ban_pdf", args=[phieu.pk])).status_code, 404
        )


class HangThanhVienTests(TestCase):
    def test_hang_theo_chi_tieu_va_uu_dai_chi_cho_thuoc_khong_ke_don(self):
        from django.utils import timezone

        from ..models import DonHang, LichSuDonHang
        from ..services.dat_hang import dat_giu
        from ..thanh_vien import hang_cua

        d = tao_du_lieu()
        tao_ton(d, luong=500)
        self.assertEqual(hang_cua(d.khach)["ten"], "Thành viên")
        cu = dat_giu(d.khach, d.cn, [{"thuoc": d.thuoc, "so_luong": 1}])
        DonHang.objects.filter(pk=cu.pk).update(
            trang_thai="hoan_thanh", tien_hang=3_200_000, tong_thanh_toan=3_200_000
        )
        hang = hang_cua(d.khach)
        self.assertEqual((hang["ten"], hang["phan_tram"], hang["hang_sau"]), ("Bạc", 3, "Vàng"))
        don = dat_giu(d.khach, d.cn, [{"thuoc": d.thuoc, "so_luong": 100}])
        self.assertEqual(
            (don.tien_hang, don.giam_gia_thanh_vien, don.tong_thanh_toan), (200000, 6000, 194000)
        )
        d.thuoc.la_thuoc_ke_don = True
        d.thuoc.save()
        don_ke_don = dat_giu(d.khach, d.cn, [{"thuoc": d.thuoc, "so_luong": 10}])
        self.assertEqual(don_ke_don.giam_gia_thanh_vien, 0)
        self.client.force_login(d.khach)
        self.assertContains(self.client.get(reverse("tai_khoan:cua_toi")), "Bạc")
        self.assertTrue(LichSuDonHang.objects.exists() and timezone.now())
