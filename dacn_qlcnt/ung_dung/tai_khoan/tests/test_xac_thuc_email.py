import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ung_dung.thong_bao.models import NhatKyEmail

from ..models import PhienXacThuc

MAT_KHAU = "Mat-khau-test-2026!"


def lay_ma(thu):
    return re.search(r"\b(\d{6})\b", thu.body).group(1)


class DangKyTests(TestCase):
    def dang_ky(self, **them):
        du_lieu = {
            "ho_ten": "Nguyễn Văn An",
            "email": "  An.Nguyen@Example.com ",
            "so_dien_thoai": "+84 901 234 567",
            "ten_dang_nhap": "an.nguyen",
            "mat_khau": MAT_KHAU,
            "nhap_lai_mat_khau": MAT_KHAU,
            **them,
        }
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("tai_khoan:dang_ky"), du_lieu)

    def test_dang_ky_qua_otp_tao_tai_khoan_da_xac_thuc(self):
        phan_hoi = self.dang_ky()
        phien = PhienXacThuc.objects.get()
        self.assertRedirects(
            phan_hoi, reverse("tai_khoan:xac_thuc_dang_ky", args=[phien.ma_phien_xac_thuc])
        )
        self.assertEqual(phien.email, "an.nguyen@example.com")
        self.assertEqual(phien.so_dien_thoai_dang_ky, "0901234567")
        self.assertFalse(get_user_model().objects.filter(ten_dang_nhap="an.nguyen").exists())
        ma = lay_ma(mail.outbox[0])
        self.assertNotIn(ma, phien.bam_otp)
        nhat_ky = NhatKyEmail.objects.get(loai_email="ma_xac_thuc")
        self.assertEqual(nhat_ky.trang_thai, "da_gui")
        self.assertNotIn(ma, nhat_ky.noi_dung_van_ban)
        with self.captureOnCommitCallbacks(execute=True):
            phan_hoi = self.client.post(phan_hoi.url, {"ma_otp": ma})
        self.assertRedirects(phan_hoi, reverse("tai_khoan:cua_toi"))
        tai_khoan = get_user_model().objects.get(ten_dang_nhap="an.nguyen")
        self.assertTrue(tai_khoan.da_xac_thuc_email)
        self.assertEqual(tai_khoan.vai_tro, "khach_hang")
        self.assertTrue(tai_khoan.check_password(MAT_KHAU))
        self.assertEqual(mail.outbox[-1].to, ["an.nguyen@example.com"])
        self.assertIn("Chào mừng", mail.outbox[-1].subject)
        self.assertEqual(int(self.client.session["_auth_user_id"]), tai_khoan.pk)

    def test_ma_dung_khong_dung_lai_lan_hai(self):
        url = self.dang_ky().url
        ma = lay_ma(mail.outbox[0])
        self.client.post(url, {"ma_otp": ma})
        self.client.logout()
        # Phiên vẫn gắn session cũ đã bị logout xóa nên trang trả 404.
        self.assertEqual(self.client.post(url, {"ma_otp": ma}).status_code, 404)

    def test_nhap_sai_nam_lan_khoa_phien(self):
        url = self.dang_ky().url
        ma = lay_ma(mail.outbox[0])
        sai = "000000" if ma != "000000" else "111111"
        for lan in range(5):
            phan_hoi = self.client.post(url, {"ma_otp": sai})
            self.assertEqual(PhienXacThuc.objects.get().so_lan_nhap_sai, lan + 1)
        self.assertContains(phan_hoi, "Phiên đã bị khóa")
        phan_hoi = self.client.post(url, {"ma_otp": ma})
        self.assertContains(phan_hoi, "nhập sai quá 5 lần")
        self.assertFalse(get_user_model().objects.filter(ten_dang_nhap="an.nguyen").exists())

    def test_ma_het_han(self):
        url = self.dang_ky().url
        PhienXacThuc.objects.update(
            thoi_diem_gui_cuoi=timezone.now() - timedelta(minutes=20),
            thoi_diem_het_han=timezone.now() - timedelta(minutes=10),
        )
        phan_hoi = self.client.post(url, {"ma_otp": lay_ma(mail.outbox[0])})
        self.assertContains(phan_hoi, "Mã đã hết hạn")

    def test_gui_lai_phai_cho_60_giay_va_doi_ma(self):
        url = self.dang_ky().url
        phien = PhienXacThuc.objects.get()
        url_gui_lai = reverse("tai_khoan:gui_lai_ma", args=[phien.ma_phien_xac_thuc])
        self.client.post(url_gui_lai)
        self.assertEqual(len(mail.outbox), 1)
        PhienXacThuc.objects.update(thoi_diem_gui_cuoi=timezone.now() - timedelta(seconds=61))
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(url_gui_lai)
        self.assertEqual(len(mail.outbox), 2)
        ma_cu, ma_moi = lay_ma(mail.outbox[0]), lay_ma(mail.outbox[1])
        if ma_cu != ma_moi:
            self.assertContains(self.client.post(url, {"ma_otp": ma_cu}), "Mã không đúng")
        self.assertRedirects(
            self.client.post(url, {"ma_otp": ma_moi}), reverse("tai_khoan:cua_toi")
        )

    def test_trinh_duyet_khac_khong_mo_duoc_trang_nhap_ma(self):
        url = self.dang_ky().url
        self.client.cookies.clear()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_trung_ten_hoac_email(self):
        get_user_model().objects.create_user("an.nguyen", MAT_KHAU, email="khac@example.com")
        self.assertContains(self.dang_ky(), "Tên đăng nhập đã được sử dụng")
        phan_hoi = self.dang_ky(ten_dang_nhap="ten_khac", email="khac@example.com")
        self.assertEqual(phan_hoi.status_code, 302)
        self.assertNotIn("Email đã được dùng", phan_hoi.content.decode())

    def test_gioi_han_nam_phien_moi_gio(self):
        for so in range(5):
            self.dang_ky(ten_dang_nhap=f"nguoi{so}x")
        self.assertContains(self.dang_ky(ten_dang_nhap="nguoi9x"), "quá nhiều mã")


class KhoiPhucTests(TestCase):
    def setUp(self):
        self.tai_khoan = get_user_model().objects.create_user(
            "khach_cu", MAT_KHAU, email="khach@example.com", ho_ten="Lê Thu"
        )

    def test_quen_mat_khau_dat_lai_bang_ma(self):
        with self.captureOnCommitCallbacks(execute=True):
            phan_hoi = self.client.post(
                reverse("tai_khoan:quen_mat_khau"), {"email": "KHACH@example.com"}
            )
        ma = lay_ma(mail.outbox[0])
        moi = "Mat-khau-moi-2027!"
        with self.captureOnCommitCallbacks(execute=True):
            ket_qua = self.client.post(
                phan_hoi.url,
                {"ma_otp": ma, "mat_khau_moi": moi, "nhap_lai_mat_khau": moi},
            )
        self.assertRedirects(ket_qua, reverse("tai_khoan:dang_nhap"))
        self.tai_khoan.refresh_from_db()
        self.assertTrue(self.tai_khoan.check_password(moi))
        self.assertIn("Mật khẩu", mail.outbox[-1].subject)

    def test_email_la_phan_hoi_giong_het_va_khong_gui(self):
        with self.captureOnCommitCallbacks(execute=True):
            phan_hoi = self.client.post(
                reverse("tai_khoan:quen_mat_khau"), {"email": "khong-co@example.com"}
            )
        self.assertEqual(phan_hoi.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
        trang = self.client.get(phan_hoi.url)
        self.assertContains(trang, "Đặt lại mật khẩu")
        loi = self.client.post(
            phan_hoi.url,
            {
                "ma_otp": "123456",
                "mat_khau_moi": "Abc-xyz-2027!",
                "nhap_lai_mat_khau": "Abc-xyz-2027!",
            },
        )
        self.assertContains(loi, "Mã không đúng")

    def test_dang_nhap_bang_email(self):
        phan_hoi = self.client.post(
            reverse("tai_khoan:dang_nhap"), {"username": "Khach@Example.com", "password": MAT_KHAU}
        )
        self.assertEqual(phan_hoi.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.tai_khoan.pk)

    def test_nhac_ten_dang_nhap_gioi_han_ba_lan_moi_gio(self):
        for _ in range(5):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(
                    reverse("tai_khoan:quen_ten_dang_nhap"), {"email": "khach@example.com"}
                )
        self.assertEqual(len(mail.outbox), 3)
        self.assertIn("khach_cu", mail.outbox[0].body)

    def test_doi_email_can_mat_khau_va_ma_gui_toi_email_moi(self):
        self.client.force_login(self.tai_khoan)
        sai = self.client.post(
            reverse("tai_khoan:doi_email"),
            {"email_moi": "moi@example.com", "mat_khau_hien_tai": "sai"},
        )
        self.assertContains(sai, "Mật khẩu hiện tại không đúng")
        with self.captureOnCommitCallbacks(execute=True):
            phan_hoi = self.client.post(
                reverse("tai_khoan:doi_email"),
                {"email_moi": "moi@example.com", "mat_khau_hien_tai": MAT_KHAU},
            )
        self.assertEqual(mail.outbox[0].to, ["moi@example.com"])
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(phan_hoi.url, {"ma_otp": lay_ma(mail.outbox[0])})
        self.tai_khoan.refresh_from_db()
        self.assertEqual(self.tai_khoan.email, "moi@example.com")
        self.assertEqual(mail.outbox[-1].to, ["moi@example.com"])
        self.assertEqual(mail.outbox[-2].to, ["khach@example.com"])
        self.assertIn("mo*@example.com", mail.outbox[-2].body)
        self.assertIn("/khoi-phuc-email/", mail.outbox[-2].body)
        thu_cu = NhatKyEmail.objects.get(loai_email="email_da_doi")
        self.assertNotIn("/khoi-phuc-email/", thu_cu.noi_dung_van_ban)
        self.assertNotIn("/khoi-phuc-email/", thu_cu.noi_dung_html)

    def test_doi_mat_khau_giu_phien_dang_nhap_va_bao_email(self):
        self.client.force_login(self.tai_khoan)
        moi = "Mat-khau-moi-2027!"
        with self.captureOnCommitCallbacks(execute=True):
            phan_hoi = self.client.post(
                reverse("tai_khoan:doi_mat_khau"),
                {"mat_khau_hien_tai": MAT_KHAU, "mat_khau_moi": moi, "nhap_lai_mat_khau": moi},
            )
        self.assertRedirects(phan_hoi, reverse("tai_khoan:doi_mat_khau"))
        self.assertEqual(self.client.get(reverse("tai_khoan:cua_toi")).status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
