from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from ung_dung.chung.van_ban import cat_khoang_trang


class DangNhapForm(AuthenticationForm):
    username = forms.CharField(label="Tên đăng nhập", max_length=150)
    password = forms.CharField(label="Mật khẩu", widget=forms.PasswordInput, strip=False)

    def clean_username(self):
        return cat_khoang_trang(self.cleaned_data["username"])


class DangKyForm(forms.Form):
    ten_dang_nhap = forms.CharField(label="Tên đăng nhập", max_length=150)
    mat_khau = forms.CharField(label="Mật khẩu", widget=forms.PasswordInput, strip=False)
    nhap_lai_mat_khau = forms.CharField(
        label="Nhập lại mật khẩu", widget=forms.PasswordInput, strip=False
    )

    def clean_ten_dang_nhap(self):
        ten = cat_khoang_trang(self.cleaned_data["ten_dang_nhap"])
        if get_user_model().objects.filter(ten_dang_nhap=ten).exists():
            raise ValidationError("Tên đăng nhập đã được sử dụng.")
        return ten

    def clean(self):
        du_lieu = super().clean()
        if du_lieu.get("mat_khau") != du_lieu.get("nhap_lai_mat_khau"):
            raise ValidationError("Hai mật khẩu không khớp.")
        return du_lieu


class TaiKhoanForm(forms.ModelForm):
    mat_khau = forms.CharField(
        label="Mật khẩu mới (để trống nếu giữ nguyên)",
        widget=forms.PasswordInput,
        required=False,
        strip=False,
    )
    ten_dang_nhap = forms.CharField(label="Tên đăng nhập", max_length=150)

    def clean_ten_dang_nhap(self):
        return cat_khoang_trang(self.cleaned_data["ten_dang_nhap"])

    class Meta:
        model = get_user_model()
        fields = ["ten_dang_nhap", "vai_tro", "chi_nhanh", "dang_hoat_dong"]
        labels = {
            "ten_dang_nhap": "Tên đăng nhập",
            "vai_tro": "Vai trò",
            "chi_nhanh": "Chi nhánh",
            "dang_hoat_dong": "Đang hoạt động",
        }
