from django.test import SimpleTestCase

from ..models import DonHang


class NhanThanhToanKhachTests(SimpleTestCase):
    """Tình trạng tiền hiện cho khách (trang đơn, email): đơn đặt giữ trả tiền tại quầy."""

    def test_dang_giu_ghi_tra_tai_quay(self):
        don = DonHang(trang_thai="dang_giu")
        self.assertEqual(don.nhan_thanh_toan_khach, "Trả tại quầy khi nhận hàng")
        self.assertEqual(don.lop_nhan_thanh_toan_khach, "chua_thanh_toan")

    def test_da_nhan_hang_la_da_thanh_toan_tai_quay(self):
        don = DonHang(trang_thai="hoan_thanh")
        self.assertEqual(don.nhan_thanh_toan_khach, "Đã thanh toán tại quầy")
        self.assertEqual(don.lop_nhan_thanh_toan_khach, "da_thanh_toan")

    def test_huy_hoac_het_han_khong_phat_sinh_tien(self):
        for trang_thai in ("da_huy", "het_han"):
            with self.subTest(trang_thai=trang_thai):
                don = DonHang(trang_thai=trang_thai)
                self.assertEqual(don.nhan_thanh_toan_khach, "Không phát sinh thanh toán")
                self.assertEqual(don.lop_nhan_thanh_toan_khach, "khong_thu")
