"""Hành vi giao diện cho người dùng hằng ngày: menu theo vai trò, cảnh báo kho, màn bán, danh sách."""

import re

from django.test import TestCase
from django.urls import reverse

from ung_dung.ban_hang.services.phieu_ban import ban_tai_quay
from ung_dung.kho.services.giao_dich import ma_chung_tu
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton


class TraiNghiemTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_ma_chung_tu_ngan_doc_duoc(self):
        self.assertRegex(ma_chung_tu("BH"), r"^BH-\d{6}-[0-9A-HJKMNP-TV-Z]{6}$")

    def test_menu_nhan_vien_an_danh_muc_cau_hinh_va_ban_mo_man_ban(self):
        self.client.force_login(self.d.nv)
        trang = self.client.get(reverse("chung:bang_dieu_khien"))
        menu = {m["ten"]: m for m in trang.context["menu_ung_dung"]}
        self.assertNotIn("danh_muc:nhom_atc_danh_sach", menu)
        self.assertNotIn("danh_muc:don_vi_tinh_danh_sach", menu)
        self.assertIn("danh_muc:thuoc_danh_sach", menu)
        self.assertEqual(
            menu["ban_hang:phieu_ban_danh_sach"]["duong_dan"], reverse("ban_hang:phieu_ban_tao")
        )
        # Ẩn khỏi menu nhưng quyền xem vẫn giữ nguyên.
        self.assertEqual(
            self.client.get(reverse("danh_muc:don_vi_tinh_danh_sach")).status_code, 200
        )

    def test_canh_bao_kho_phan_muc_va_goi_y_viec_lam(self):
        tao_ton(self.d, "LO-QUA-HAN", ngay=-3, luong=5)
        tao_ton(self.d, "LO-GAN-HAN", ngay=4, luong=7)
        tao_ton(self.d, "LO-KHOA", ngay=200, luong=2, duoc_ban=False)
        self.client.force_login(self.d.ql)
        url = reverse("kho:canh_bao")
        trang = self.client.get(url)
        # Mặc định mở thẻ gấp nhất đang có việc.
        self.assertEqual(trang.context["muc"], "het_han")

        def cac_lo(**tham_so):
            return [d.lo_thuoc.ma_lo_thuoc for d in self.client.get(url, tham_so).context["trang"]]

        self.assertEqual(cac_lo(muc="het_han"), ["LO-QUA-HAN"])
        self.assertEqual(cac_lo(muc="duoi_7"), ["LO-GAN-HAN"])
        self.assertEqual(cac_lo(muc="khoa_ban"), ["LO-KHOA"])
        self.assertEqual(cac_lo(muc="duoi_7", tim="LO-GAN"), ["LO-GAN-HAN"])
        self.assertEqual(cac_lo(muc="duoi_7", tim="khong-co"), [])
        so = {the["ma"]: the["so"] for the in trang.context["cac_the"]}
        self.assertEqual((so["het_han"], so["duoi_7"], so["khoa_ban"]), (1, 1, 1))
        self.assertContains(trang, "Đã quá 3 ngày")
        self.assertContains(trang, reverse("kho:phieu_xuat_huy_tao") + "?loai=het_han")
        # Phân trang: 1 dòng/trang không có trong lựa chọn nên giữ mặc định, trang lạ về trang cuối.
        self.assertEqual(self.client.get(url, {"muc": "het_han", "page": "99"}).status_code, 200)

    def test_man_ban_giu_lai_dong_khi_loi_va_ban_thanh_cong(self):
        tao_ton(self.d, luong=3)
        self.client.force_login(self.d.nv)
        url = reverse("ban_hang:phieu_ban_tao")
        trang = self.client.get(url)
        self.assertContains(trang, 'id="du-lieu-quay"')
        du_lieu = {
            "chi_nhanh": self.d.cn.pk,
            "khoa_yeu_cau": "3f2a1c4e-0000-4000-8000-000000000001",
            "phuong_thuc_thanh_toan": "tien_mat",
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "1",
            "form-MAX_NUM_FORMS": "50",
            "form-0-thuoc": self.d.thuoc.pk,
            "form-0-so_luong": "9",
            "form-0-quy_doi_bao_goi": "",
        }
        loi = self.client.post(url, du_lieu)
        self.assertEqual(loi.status_code, 200)
        self.assertEqual(
            loi.context["dong_ban_dau"],
            [{"thuoc": self.d.thuoc.pk, "so_luong": 9, "bao_goi": None}],
        )
        du_lieu["form-0-so_luong"] = "2"
        du_lieu["khoa_yeu_cau"] = "3f2a1c4e-0000-4000-8000-000000000002"
        thanh_cong = self.client.post(url, du_lieu)
        self.assertEqual(thanh_cong.status_code, 302)

    def test_ton_kho_mac_dinh_an_lo_da_het(self):
        tao_ton(self.d, "LO-CON", luong=4)
        tao_ton(self.d, "LO-HET", luong=0)
        self.client.force_login(self.d.ql)
        url = reverse("kho:ton_kho_danh_sach")
        mac_dinh = [d.lo_thuoc.ma_lo_thuoc for d in self.client.get(url).context["trang"]]
        self.assertEqual(mac_dinh, ["LO-CON"])
        tat_ca = [
            d.lo_thuoc.ma_lo_thuoc
            for d in self.client.get(url, {"con_hang": "tat_ca"}).context["trang"]
        ]
        self.assertCountEqual(tat_ca, ["LO-CON", "LO-HET"])

    def test_danh_sach_phieu_ban_co_tong_tien_va_cach_tra(self):
        tao_ton(self.d, luong=10)
        ban_tai_quay(
            self.d.nv,
            self.d.cn,
            [{"thuoc": self.d.thuoc, "so_luong": 3}],
            phuong_thuc_thanh_toan="chuyen_khoan",
        )
        self.client.force_login(self.d.nv)
        trang = self.client.get(reverse("ban_hang:phieu_ban_danh_sach"))
        phieu = trang.context["trang"][0]
        self.assertEqual(
            (phieu.so_mat_hang, phieu.tong_tien, phieu.cach_tra), (1, 6000, "Chuyển khoản")
        )
        self.assertTrue(re.match(r"^BH-\d{6}-", phieu.ma_phieu_ban))
        self.assertContains(trang, "6.000 đ")
        self.assertFalse(trang.context["nhieu_chi_nhanh"])

    def test_don_dang_giu_hien_viec_can_lam_va_gom_thao_tac_phu(self):
        from ung_dung.ban_hang.services.dat_hang import dat_hang

        tao_ton(self.d, luong=10)
        don = dat_hang(self.d.khach, self.d.cn, [{"thuoc": self.d.thuoc, "so_luong": 1}])
        self.client.force_login(self.d.nv)
        trang = self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[don.pk]))
        self.assertContains(trang, "Giao đơn tại quầy")
        self.assertContains(trang, "Khách không đến nhận hoặc muốn hủy?")
        self.assertTrue(trang.context["co_hanh_dong_phu"])

    def test_form_phieu_nhap_giu_an_dong_da_bo_khi_bao_loi(self):
        self.client.force_login(self.d.ql)
        url = reverse("kho:phieu_nhap_tao")
        trang = self.client.get(url)
        self.assertContains(trang, "Lưu phiếu nhập")
        self.assertContains(trang, "Các lô nhận được")
        loi = self.client.post(
            url,
            {
                "chi_nhanh": self.d.cn.pk,
                "nha_cung_cap": "",
                "form-TOTAL_FORMS": "2",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "1",
                "form-MAX_NUM_FORMS": "50",
                "form-0-thuoc": self.d.thuoc.pk,
                "form-0-so_luong": "5",
                "form-1-so_luong": "3",
                "form-1-DELETE": "on",
            },
        )
        self.assertEqual(loi.status_code, 200)
        self.assertContains(loi, "data-dong hidden", count=1)
