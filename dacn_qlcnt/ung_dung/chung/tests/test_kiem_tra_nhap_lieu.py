"""Ràng buộc số điện thoại / email / họ tên kiểu Việt Nam và lời báo lỗi tiếng Việt toàn hệ thống."""

from unittest import mock

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from ung_dung.chung.truong_form import TruongEmail, TruongHoTen, TruongSoDienThoai
from ung_dung.tai_khoan.models import TaiKhoan


def loi(truong, gia_tri):
    try:
        truong.clean(gia_tri)
    except ValidationError as e:
        return e.messages[0]
    return None


class TruongNhapLieuTests(SimpleTestCase):
    def test_so_dien_thoai_viet_nam(self):
        truong = TruongSoDienThoai()
        self.assertEqual(truong.clean("+84 912 345 678"), "0912345678")
        self.assertEqual(truong.clean("0912.345.678"), "0912345678")
        self.assertEqual(truong.clean("028 3812 3456"), "02838123456")
        self.assertIn("không phải đầu số di động", loi(truong, "0123456789"))
        self.assertIn("0000000000"[:3], loi(truong, "0000000000"))
        self.assertIn("01x", loi(truong, "01681234567"))
        self.assertIn("10 chữ số", loi(truong, "091234567"))
        self.assertIn("chỉ gồm chữ số", loi(truong, "09abc12345"))
        self.assertIn("1800/1900", loi(truong, "19001234"))
        self.assertIn("di động", loi(TruongSoDienThoai(loai="di_dong"), "02838123456"))
        self.assertEqual(TruongSoDienThoai(loai="hotline").clean("1900 1234"), "19001234")

    def test_email_va_ho_ten(self):
        email = TruongEmail()
        self.assertEqual(email.clean(" Ten.Ban@Gmail.com "), "ten.ban@gmail.com")
        self.assertIn("ten@gmail.com", loi(email, "ten@gmail.con"))
        self.assertIn("@", loi(email, "tengmail.com"))
        self.assertIn("không dấu", loi(email, "nguyễn@gmail.com"))
        ho_ten = TruongHoTen()
        self.assertEqual(ho_ten.clean("  Nguyễn   Văn An "), "Nguyễn Văn An")
        self.assertIn("chữ số", loi(ho_ten, "An 123"))
        self.assertIn("chữ cái", loi(ho_ten, "@@"))

    def test_loi_mac_dinh_tieng_viet(self):
        class F(forms.Form):
            ten = forms.CharField(max_length=3)
            so = forms.IntegerField(max_value=5)
            chon = forms.ChoiceField(choices=[("a", "A")])
            dong_y = forms.BooleanField()

        form = F({"ten": "abcd", "so": "9", "chon": "x"})
        form.is_valid()
        self.assertEqual(form.errors["ten"], ["Tối đa 3 ký tự (bạn đã nhập 4)."])
        self.assertEqual(form.errors["so"], ["Giá trị tối đa là 5."])
        self.assertIn("chọn lại", form.errors["chon"][0])
        self.assertEqual(form.errors["dong_y"], ["Vui lòng đánh dấu ô này để tiếp tục."])
        self.assertEqual(F({}).errors["ten"], ["Vui lòng nhập thông tin này."])
        with self.assertRaises(ValidationError) as ngu_canh:
            validate_password("1234567")
        self.assertIn("Mật khẩu quá ngắn: cần ít nhất 8 ký tự.", ngu_canh.exception.messages)


class RangBuocCsdlTests(TestCase):
    def test_csdl_tu_choi_so_dien_thoai_sai(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TaiKhoan.objects.create_user("so_sai", so_dien_thoai="0123456789")
        TaiKhoan.objects.create_user("so_dung", so_dien_thoai="0912345678")


class GuiMaLoiTests(TestCase):
    def test_trang_nhap_ma_bao_khi_gui_email_loi(self):
        du_lieu = {
            "ho_ten": "Nguyễn Văn An",
            "email": "an.nguyen@gmail.com",
            "so_dien_thoai": "0912 345 678",
            "ten_dang_nhap": "an_nguyen",
            "mat_khau": "Mat-khau-rat-kho-2026",
            "nhap_lai_mat_khau": "Mat-khau-rat-kho-2026",
        }
        with (
            mock.patch(
                "django.core.mail.EmailMultiAlternatives.send", side_effect=OSError("mất mạng")
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            phan_hoi = self.client.post(reverse("tai_khoan:dang_ky"), du_lieu)
        self.assertContains(self.client.get(phan_hoi["Location"]), "Chưa gửi được email chứa mã")
        sai = self.client.post(reverse("tai_khoan:dang_ky"), {**du_lieu, "so_dien_thoai": "0123"})
        self.assertContains(sai, "Số di động gồm 10 chữ số")
