from django.test import SimpleTestCase

from ..models import DonHang


class NhanThanhToanKhachTests(SimpleTestCase):
    """Tình trạng thanh toán hiện cho khách (trang đơn, email) theo Q43."""

    def don(self, **gia_tri):
        return DonHang(
            **{
                "hinh_thuc_nhan": "giao_hang",
                "phuong_thuc_thanh_toan": "cod",
                "trang_thai": "cho_xac_nhan",
                "trang_thai_thanh_toan": "chua_thanh_toan",
                **gia_tri,
            }
        )

    def test_cod_da_giao_xong_la_da_tra_cho_nguoi_giao(self):
        don = self.don(trang_thai="hoan_thanh")
        self.assertEqual(don.nhan_thanh_toan_khach, "Đã trả cho người giao")
        self.assertEqual(don.lop_nhan_thanh_toan_khach, "da_thanh_toan")
        # Trạng thái nội bộ không đổi: nhà thuốc vẫn chờ người giao nộp tiền.
        self.assertEqual(don.trang_thai_thanh_toan, "chua_thanh_toan")

    def test_cod_chua_giao_ghi_tra_khi_nhan_hang(self):
        for trang_thai in ("cho_xac_nhan", "dang_chuan_bi", "dang_giao"):
            with self.subTest(trang_thai=trang_thai):
                don = self.don(trang_thai=trang_thai)
                self.assertEqual(don.nhan_thanh_toan_khach, "Trả khi nhận hàng")
                self.assertEqual(don.lop_nhan_thanh_toan_khach, "chua_thanh_toan")

    def test_don_giu_tai_quay_ghi_tra_tai_quay(self):
        don = self.don(
            hinh_thuc_nhan="nhan_tai_quay", phuong_thuc_thanh_toan="tai_quay", trang_thai="dang_giu"
        )
        self.assertEqual(don.nhan_thanh_toan_khach, "Trả tại quầy khi nhận hàng")

    def test_don_con_di_tiep_ma_cho_hoan_thi_noi_ro_da_thanh_toan(self):
        don = self.don(phuong_thuc_thanh_toan="chuyen_khoan", trang_thai_thanh_toan="cho_hoan_tien")
        self.assertEqual(don.nhan_thanh_toan_khach, "Đã thanh toán, có khoản chờ hoàn")
        don.trang_thai = "da_huy"
        self.assertEqual(don.nhan_thanh_toan_khach, "Chờ hoàn tiền")

    def test_trang_thai_khac_giu_nhan_goc(self):
        self.assertEqual(self.don(trang_thai="da_huy").nhan_thanh_toan_khach, "Chưa thanh toán")
        for ma, nhan in (
            ("da_thanh_toan", "Đã thanh toán"),
            ("da_hoan_tien", "Đã hoàn tiền"),
        ):
            with self.subTest(ma=ma):
                don = self.don(trang_thai="hoan_thanh", trang_thai_thanh_toan=ma)
                self.assertEqual(don.nhan_thanh_toan_khach, nhan)
                self.assertEqual(don.lop_nhan_thanh_toan_khach, ma)
