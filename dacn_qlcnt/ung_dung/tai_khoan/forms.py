from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from ung_dung.chung.truong_form import TruongEmail, TruongMotDong, TruongSoDienThoai
from ung_dung.chung.van_ban import cat_khoang_trang

MAU_TEN_DANG_NHAP = r"^[A-Za-z0-9._-]{4,30}$"
# Khung tọa độ lãnh thổ Việt Nam (đất liền và đảo gần bờ) để chặn điểm ghim nhầm.
VI_DO_VN = (8.0, 23.5)
KINH_DO_VN = (102.0, 110.0)


def _o_mat_khau(nhan, autocomplete="new-password", **kwargs):
    return forms.CharField(
        label=nhan,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": autocomplete}),
        **kwargs,
    )


class KiemHaiMatKhau:
    """Kiểm hai ô mật khẩu khớp nhau; dùng chung cho đăng ký và đặt lại."""

    o_mat_khau = "mat_khau"

    def clean(self):
        du_lieu = super().clean()
        if du_lieu.get(self.o_mat_khau) != du_lieu.get("nhap_lai_mat_khau"):
            self.add_error("nhap_lai_mat_khau", "Hai mật khẩu không khớp.")
        return du_lieu


class DangNhapForm(AuthenticationForm):
    username = forms.CharField(
        label="Tên đăng nhập hoặc email",
        max_length=254,
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )
    password = _o_mat_khau("Mật khẩu", "current-password")
    error_messages = {
        "invalid_login": "Tên đăng nhập hoặc mật khẩu không đúng.",
        "inactive": "Tài khoản đang bị khóa. Vui lòng liên hệ nhà thuốc.",
    }

    def clean_username(self):
        dang_nhap = cat_khoang_trang(self.cleaned_data["username"])
        if "@" in dang_nhap:
            tai_khoan = get_user_model().objects.filter(email=dang_nhap.lower()).first()
            if tai_khoan:
                return tai_khoan.ten_dang_nhap
        return dang_nhap


class DangKyForm(KiemHaiMatKhau, forms.Form):
    ho_ten = TruongMotDong(
        label="Họ và tên", max_length=100, widget=forms.TextInput(attrs={"autocomplete": "name"})
    )
    email = TruongEmail(label="Email", help_text="Mã xác thực sẽ gửi tới email này.")
    so_dien_thoai = TruongSoDienThoai(label="Số điện thoại", required=False)
    ten_dang_nhap = forms.RegexField(
        label="Tên đăng nhập",
        regex=MAU_TEN_DANG_NHAP,
        help_text="4–30 ký tự: chữ không dấu, số, dấu chấm, gạch dưới hoặc gạch ngang.",
        error_messages={"invalid": "Tên đăng nhập chỉ gồm chữ không dấu, số và . _ -"},
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    mat_khau = _o_mat_khau("Mật khẩu", help_text="Ít nhất 8 ký tự, không quá đơn giản.")
    nhap_lai_mat_khau = _o_mat_khau("Nhập lại mật khẩu")


class MaOTPForm(forms.Form):
    ma_otp = forms.RegexField(
        label="Mã xác thực",
        regex=r"^[0-9]{6}$",
        error_messages={"invalid": "Mã gồm đúng 6 chữ số."},
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "maxlength": 6,
                "autofocus": True,
                "class": "o-ma-otp",
            }
        ),
    )

    def clean_ma_otp(self):
        return cat_khoang_trang(self.cleaned_data["ma_otp"])


class DatLaiMatKhauForm(KiemHaiMatKhau, MaOTPForm):
    o_mat_khau = "mat_khau_moi"
    mat_khau_moi = _o_mat_khau("Mật khẩu mới")
    nhap_lai_mat_khau = _o_mat_khau("Nhập lại mật khẩu mới")


class EmailForm(forms.Form):
    email = TruongEmail(label="Email đã đăng ký")


class HoSoForm(forms.Form):
    ho_ten = TruongMotDong(
        label="Họ và tên", max_length=100, widget=forms.TextInput(attrs={"autocomplete": "name"})
    )
    so_dien_thoai = TruongSoDienThoai(label="Số điện thoại", required=False)


class DoiMatKhauForm(KiemHaiMatKhau, forms.Form):
    o_mat_khau = "mat_khau_moi"
    mat_khau_hien_tai = _o_mat_khau("Mật khẩu hiện tại", "current-password")
    mat_khau_moi = _o_mat_khau("Mật khẩu mới")
    nhap_lai_mat_khau = _o_mat_khau("Nhập lại mật khẩu mới")


class DoiEmailForm(forms.Form):
    email_moi = TruongEmail(label="Email mới")
    mat_khau_hien_tai = _o_mat_khau("Mật khẩu hiện tại", "current-password")


class DiaChiGiaoHangForm(forms.Form):
    ten_nguoi_nhan = TruongMotDong(label="Người nhận", max_length=100)
    so_dien_thoai = TruongSoDienThoai(label="Số điện thoại người nhận")
    dia_chi = TruongMotDong(
        label="Địa chỉ",
        max_length=300,
        help_text="Số nhà, tên đường, phường/xã, tỉnh/thành phố.",
        widget=forms.TextInput(attrs={"autocomplete": "street-address"}),
    )
    ghi_chu = TruongMotDong(label="Ghi chú cho người giao", max_length=200, required=False)
    vi_do = forms.FloatField(widget=forms.HiddenInput, min_value=VI_DO_VN[0], max_value=VI_DO_VN[1])
    kinh_do = forms.FloatField(
        widget=forms.HiddenInput, min_value=KINH_DO_VN[0], max_value=KINH_DO_VN[1]
    )
    dat_mac_dinh = forms.BooleanField(label="Đặt làm địa chỉ mặc định", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        thong_bao = "Hãy ghim vị trí giao hàng trên bản đồ (trong lãnh thổ Việt Nam)."
        for ten in ("vi_do", "kinh_do"):
            self.fields[ten].error_messages.update(
                {"required": thong_bao, "min_value": thong_bao, "max_value": thong_bao}
            )

    @classmethod
    def tu_dia_chi(cls, dia_chi, mac_dinh):
        return cls(
            initial={
                "ten_nguoi_nhan": dia_chi.ten_nguoi_nhan,
                "so_dien_thoai": dia_chi.so_dien_thoai,
                "dia_chi": dia_chi.dia_chi,
                "ghi_chu": dia_chi.ghi_chu,
                "vi_do": dia_chi.vi_tri.y,
                "kinh_do": dia_chi.vi_tri.x,
                "dat_mac_dinh": mac_dinh,
            }
        )


class TaiKhoanForm(forms.ModelForm):
    ten_dang_nhap = forms.CharField(label="Tên đăng nhập", max_length=150)
    ho_ten = TruongMotDong(label="Họ và tên", max_length=100, required=False)
    email = TruongEmail(label="Email", required=False)
    so_dien_thoai = TruongSoDienThoai(label="Số điện thoại", required=False)
    mat_khau = forms.CharField(
        label="Mật khẩu mới (để trống nếu giữ nguyên)",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        required=False,
        strip=False,
    )

    def clean_ten_dang_nhap(self):
        return cat_khoang_trang(self.cleaned_data["ten_dang_nhap"])

    def clean_email(self):
        email = self.cleaned_data["email"] or None
        trung = get_user_model().objects.filter(email=email).exclude(pk=self.instance.pk)
        if email and trung.exists():
            raise ValidationError("Email đã được dùng cho tài khoản khác.")
        return email

    class Meta:
        model = get_user_model()
        fields = [
            "ten_dang_nhap",
            "ho_ten",
            "email",
            "so_dien_thoai",
            "vai_tro",
            "chi_nhanh",
            "dang_hoat_dong",
        ]
        labels = {
            "vai_tro": "Vai trò",
            "chi_nhanh": "Chi nhánh",
            "dang_hoat_dong": "Đang hoạt động",
        }
