from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from ..models import DiaChiGiaoHang
from ..services.dia_chi_giao_hang import dat_mac_dinh, luu_dia_chi, xoa_dia_chi

DU_LIEU = {
    "ten_nguoi_nhan": "Trần Bình",
    "so_dien_thoai": "0912345678",
    "dia_chi": "12 Nguyễn Huệ, Phường Sài Gòn, TP.HCM",
    "ghi_chu": "",
    "vi_do": 10.7743,
    "kinh_do": 106.7038,
}


class SoDiaChiTests(TestCase):
    def setUp(self):
        self.khach = get_user_model().objects.create_user("khach_dc", "Mat-khau-test-2026!")
        self.khac = get_user_model().objects.create_user("khach_khac", "Mat-khau-test-2026!")

    def test_dia_chi_dau_tien_thanh_mac_dinh(self):
        dia_chi = luu_dia_chi(self.khach, DU_LIEU)
        self.khach.refresh_from_db()
        self.assertEqual(self.khach.dia_chi_giao_hang_mac_dinh, dia_chi)
        self.assertAlmostEqual(dia_chi.vi_tri.y, 10.7743)

    def test_khong_thao_tac_dia_chi_nguoi_khac(self):
        dia_chi = luu_dia_chi(self.khach, DU_LIEU)
        with self.assertRaises(PermissionDenied):
            dat_mac_dinh(self.khac, dia_chi)
        with self.assertRaises(PermissionDenied):
            xoa_dia_chi(self.khac, dia_chi)
        self.client.force_login(self.khac)
        url = reverse("tai_khoan:sua_dia_chi", args=[dia_chi.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_xoa_mac_dinh_chuyen_sang_dia_chi_con_lai(self):
        dau = luu_dia_chi(self.khach, DU_LIEU)
        sau = luu_dia_chi(self.khach, {**DU_LIEU, "dia_chi": "Số 2 Lê Lợi, TP.HCM"})
        xoa_dia_chi(self.khach, dau)
        self.khach.refresh_from_db()
        self.assertEqual(self.khach.dia_chi_giao_hang_mac_dinh, sau)
        xoa_dia_chi(self.khach, sau)
        self.khach.refresh_from_db()
        self.assertIsNone(self.khach.dia_chi_giao_hang_mac_dinh)

    def test_toi_da_muoi_dia_chi(self):
        for so in range(10):
            luu_dia_chi(self.khach, {**DU_LIEU, "dia_chi": f"Số {so} Lê Lợi"})
        with self.assertRaises(ValidationError):
            luu_dia_chi(self.khach, DU_LIEU)

    def test_form_bat_buoc_ghim_trong_viet_nam(self):
        self.client.force_login(self.khach)
        phan_hoi = self.client.post(
            reverse("tai_khoan:them_dia_chi"), {**DU_LIEU, "vi_do": 48.85, "kinh_do": 2.35}
        )
        self.assertContains(phan_hoi, "Hãy ghim vị trí giao hàng")
        phan_hoi = self.client.post(
            reverse("tai_khoan:them_dia_chi"), {**DU_LIEU, "so_dien_thoai": "0912 345 678"}
        )
        self.assertRedirects(phan_hoi, reverse("tai_khoan:so_dia_chi"))
        self.assertEqual(DiaChiGiaoHang.objects.get().so_dien_thoai, "0912345678")

    def test_next_ngoai_website_bi_bo_qua(self):
        self.client.force_login(self.khach)
        phan_hoi = self.client.post(
            reverse("tai_khoan:them_dia_chi"), {**DU_LIEU, "next": "https://example.com/"}
        )
        self.assertRedirects(phan_hoi, reverse("tai_khoan:so_dia_chi"))
