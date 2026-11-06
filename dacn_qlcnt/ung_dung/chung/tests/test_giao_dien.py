from django.test import SimpleTestCase, override_settings


class NhanDienTrangTests(SimpleTestCase):
    @override_settings(DEBUG=True, HIEN_NHAN_DIEN_TRANG=True)
    def test_hien_du_ba_thanh_phan(self):
        phan_hoi = self.client.get("/")
        self.assertEqual(phan_hoi.status_code, 200)
        for muc in (
            "chung:trang_chu",
            "ung_dung/chung/views.py",
            "trang_chu",
            "chung/trang_chu.html",
        ):
            self.assertContains(phan_hoi, muc)

    @override_settings(DEBUG=False, HIEN_NHAN_DIEN_TRANG=True)
    def test_khong_lo_duong_dan_khi_tat_debug(self):
        phan_hoi = self.client.get("/")
        self.assertNotContains(phan_hoi, "ung_dung/chung/views.py")

    @override_settings(DEBUG=True, HIEN_NHAN_DIEN_TRANG=False)
    def test_co_the_tat_nhan_dien(self):
        self.assertNotContains(self.client.get("/"), "ung_dung/chung/views.py")

    @override_settings(DEBUG=False)
    def test_trang_404_khong_lo_ky_thuat(self):
        phan_hoi = self.client.get("/duong-dan-khong-ton-tai/")
        self.assertEqual(phan_hoi.status_code, 404)
        self.assertContains(phan_hoi, "Không tìm thấy trang", status_code=404)
        self.assertNotContains(phan_hoi, "Traceback", status_code=404)
