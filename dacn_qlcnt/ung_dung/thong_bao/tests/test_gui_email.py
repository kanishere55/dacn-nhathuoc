from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings

from ..models import NhatKyEmail
from ..services import gui_email


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
        self.assertEqual(nhat_ky.chi_tiet_loi, "OSError: Máy chủ từ chối")

    @override_settings(EMAIL_GUI_NEN=True)
    def test_backend_test_luon_gui_dong_bo(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.gui()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(NhatKyEmail.objects.get().trang_thai, "da_gui")
