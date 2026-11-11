from datetime import timedelta
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from ..models import NhatKyEmail
from ..services import gui_email, gui_lai_thu_ton


class GuiEmailTests(TestCase):
    def gui(self):
        return gui_email(
            loai_email="ma_xac_thuc",
            email_nhan="nhan@example.com",
            tieu_de="Mã xác thực",
            mau="ma_xac_thuc",
            ngu_canh={"ma_otp": "123456", "muc_dich": "thử", "so_phut": 10},
        )

    def test_chi_gui_sau_commit_va_che_ma(self):
        with self.captureOnCommitCallbacks(execute=False) as hang_doi:
            nhat_ky = self.gui()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(nhat_ky.trang_thai, "cho_gui")
        hang_doi[0]()
        nhat_ky.refresh_from_db()
        self.assertEqual(nhat_ky.trang_thai, "da_gui")
        self.assertIsNotNone(nhat_ky.thoi_diem_gui)
        self.assertIn("123456", mail.outbox[0].body)
        self.assertIn("123456", mail.outbox[0].alternatives[0].content)
        self.assertNotIn("123456", nhat_ky.noi_dung_van_ban)

    def test_loi_smtp_ghi_lai_mot_dong(self):
        with mock.patch(
            "django.core.mail.EmailMultiAlternatives.send",
            side_effect=OSError("Máy chủ\ntừ chối"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                nhat_ky = self.gui()
        nhat_ky.refresh_from_db()
        self.assertEqual(nhat_ky.trang_thai, "loi")
        self.assertEqual(
            nhat_ky.chi_tiet_loi,
            "Không kết nối được máy chủ thư. Kiểm tra mạng, EMAIL_HOST và EMAIL_PORT. "
            "Chi tiết: OSError: Máy chủ từ chối",
        )

    def test_gmail_tu_choi_dang_nhap_bao_dung_nguyen_nhan(self):
        import smtplib

        loi = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
        with mock.patch("django.core.mail.EmailMultiAlternatives.send", side_effect=loi):
            with self.captureOnCommitCallbacks(execute=True):
                nhat_ky = self.gui()
        nhat_ky.refresh_from_db()
        self.assertTrue(nhat_ky.chi_tiet_loi.startswith("Gmail từ chối đăng nhập (mã 535)"))

    @override_settings(EMAIL_GUI_NEN=True)
    def test_backend_test_luon_gui_dong_bo(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.gui()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(NhatKyEmail.objects.get().trang_thai, "da_gui")

    def test_thu_cu_dang_gui_lai_khong_the_giu_luot_lan_hai(self):
        with self.captureOnCommitCallbacks(execute=False):
            thu = gui_email(
                loai_email="nhac_ten_dang_nhap",
                email_nhan="nhan@example.com",
                tieu_de="Tên đăng nhập",
                mau="nhac_ten_dang_nhap",
                ngu_canh={"ten_dang_nhap": "thu_nghiem"},
            )
        NhatKyEmail.objects.filter(pk=thu.pk).update(
            thoi_diem_tao=timezone.now() - timedelta(hours=1)
        )

        def trong_luc_gui(_):
            self.assertEqual(gui_lai_thu_ton(), (0, 0))

        with mock.patch("ung_dung.thong_bao.services._gui", side_effect=trong_luc_gui) as gui:
            gui_lai_thu_ton()
        thu.refresh_from_db()
        self.assertEqual(gui.call_count, 1)
        self.assertEqual(thu.so_lan_gui, 2)
        self.assertIsNotNone(thu.thoi_diem_thu_lai)
