from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from ung_dung.chung.truong_form import (
    TruongEmail,
    TruongHoTen,
    TruongMotDong,
    TruongSoDienThoai,
)
from ung_dung.chung.van_ban import cat_khoang_trang

from . import quyen as danh_muc_quyen
from .models import NhomQuyen
from .services.dang_nhap import (
    SO_LAN_SAI_TOI_DA,
    ghi_dang_nhap_sai,
    thoi_diem_mo_khoa,
    tim_tai_khoan,
    xoa_dem_dang_nhap_sai,
)

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

    def clean(self):
        tai_khoan = tim_tai_khoan(self.cleaned_data.get("username"))
        if mo_khoa := thoi_diem_mo_khoa(tai_khoan):
            raise self._loi_khoa(mo_khoa)
        try:
            ket_qua = super().clean()
        except ValidationError:
            if tai_khoan and self.cleaned_data.get("password"):
                if mo_khoa := ghi_dang_nhap_sai(tai_khoan):
                    raise self._loi_khoa(mo_khoa) from None
            raise
        if self.user_cache is not None:
            xoa_dem_dang_nhap_sai(self.user_cache)
        return ket_qua

    @staticmethod
    def _loi_khoa(mo_khoa):
        gio = timezone.localtime(mo_khoa)
        return ValidationError(
            f"Nhập sai mật khẩu quá {SO_LAN_SAI_TOI_DA - 1} lần. Tài khoản tạm khóa đăng nhập "
            f"đến {gio:%H:%M}. Có thể dùng chức năng quên mật khẩu.",
            code="tam_khoa",
        )


class DangKyForm(KiemHaiMatKhau, forms.Form):
    ho_ten = TruongHoTen(label="Họ và tên")
    email = TruongEmail(label="Email", help_text="Mã xác thực sẽ gửi tới email này.")
    so_dien_thoai = TruongSoDienThoai(label="Số điện thoại", required=False)
    ten_dang_nhap = forms.RegexField(
        label="Tên đăng nhập",
        regex=MAU_TEN_DANG_NHAP,
        help_text="4–30 ký tự: chữ không dấu, số, dấu chấm, gạch dưới hoặc gạch ngang.",
        error_messages={
            "invalid": "Tên đăng nhập dài 4–30 ký tự, chỉ gồm chữ không dấu, số và . _ -",
            "required": "Vui lòng nhập tên đăng nhập.",
        },
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
    ho_ten = TruongHoTen(label="Họ và tên")
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
    ten_nguoi_nhan = TruongHoTen(label="Người nhận")
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


def _ten_o_quyen(ma):
    return "quyen__" + ma.replace(".", "__")


class TaiKhoanForm(forms.ModelForm):
    ten_dang_nhap = forms.CharField(label="Tên đăng nhập", max_length=150)
    ho_ten = TruongHoTen(label="Họ và tên", required=False)
    email = TruongEmail(label="Email", required=False)
    so_dien_thoai = TruongSoDienThoai(label="Số điện thoại", required=False)
    mat_khau = forms.CharField(
        label="Mật khẩu mới (để trống nếu giữ nguyên)",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        required=False,
        strip=False,
    )
    nhom_quyen = forms.ModelChoiceField(
        queryset=NhomQuyen.objects.all(),
        required=False,
        label="Chọn nhanh theo nhóm quyền",
        empty_label="Mặc định theo vai trò",
        help_text="Chọn nhóm để điền sẵn các quyền bên dưới, sau đó tick thêm hoặc bỏ bớt cho riêng người này.",
    )

    def __init__(self, *args, **kwargs):
        from .services.quyen import quyen_co_so, tinh_quyen_hieu_luc

        super().__init__(*args, **kwargs)
        self.fields["vai_tro"].widget.attrs["x-model"] = "vaiTro"
        self.fields["nhom_quyen"].widget.attrs["data-nhom-quyen"] = ""
        tk = self.instance
        if tk.pk and tk.vai_tro in danh_muc_quyen.MAC_DINH:
            dang_co = tinh_quyen_hieu_luc(tk)
            self.quyen_nhom_ban_dau = quyen_co_so(tk.vai_tro, tk.nhom_quyen_id)
        else:
            dang_co = self.quyen_nhom_ban_dau = quyen_co_so(danh_muc_quyen.NHAN_VIEN)
        for quyen in danh_muc_quyen.DANH_SACH_QUYEN:
            if quyen.chi_quan_tri:
                continue
            self.fields[_ten_o_quyen(quyen.ma)] = forms.BooleanField(
                label=quyen.nhan,
                required=False,
                initial=quyen.ma in dang_co,
                widget=forms.CheckboxInput(attrs={"data-ma-quyen": quyen.ma}),
            )

    def cac_nhom_quyen_rieng(self):
        """(tên nhóm, [(quyền, ô tick, có trong nhóm cơ sở)]) để vẽ bảng tick theo module."""
        return [
            (
                nhom,
                [(q, self[_ten_o_quyen(q.ma)], q.ma in self.quyen_nhom_ban_dau) for q in cac_quyen],
            )
            for nhom, cac_quyen in danh_muc_quyen.nhom_theo_module().items()
        ]

    def quyen_rieng(self):
        """So quyền được tick với quyền của nhóm: tick thêm thành cho phép, bỏ tick thành chặn.

        Trả mã quyền -> True (cho thêm), False (chặn) hoặc None (giống nhóm).
        """
        from .services.quyen import quyen_co_so

        nhom = self.cleaned_data.get("nhom_quyen")
        co_so = quyen_co_so(self.cleaned_data.get("vai_tro"), nhom.pk if nhom else None)
        ket_qua = {}
        for q in danh_muc_quyen.DANH_SACH_QUYEN:
            if q.chi_quan_tri:
                continue
            duoc_tick = bool(self.cleaned_data.get(_ten_o_quyen(q.ma)))
            ket_qua[q.ma] = None if duoc_tick == (q.ma in co_so) else duoc_tick
        return ket_qua

    def clean(self):
        du_lieu = super().clean()
        # Ô nhóm quyền chỉ hiện cho quản lý/nhân viên; giá trị cũ còn gửi lên khi đổi vai trò thì bỏ đi.
        if du_lieu.get("vai_tro") not in ("quan_ly_chi_nhanh", "nhan_vien"):
            du_lieu["nhom_quyen"] = None
        return du_lieu

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
            "nhom_quyen",
        ]
        labels = {
            "vai_tro": "Vai trò",
            "chi_nhanh": "Chi nhánh",
            "dang_hoat_dong": "Đang hoạt động",
        }


class NhomQuyenForm(forms.Form):
    ma_nhom_quyen = forms.RegexField(
        label="Mã nhóm",
        regex=r"^[A-Z0-9][A-Z0-9_-]{0,31}$",
        error_messages={
            "invalid": "Mã gồm chữ hoa, số, gạch ngang hoặc gạch dưới, tối đa 32 ký tự."
        },
        help_text="Ví dụ DUOC-SI-KHO. Không đổi được sau khi tạo.",
    )
    ten_nhom_quyen = TruongMotDong(label="Tên nhóm", max_length=100)
    mo_ta = TruongMotDong(label="Mô tả", max_length=200, required=False)
    cac_quyen = forms.MultipleChoiceField(
        label="Quyền của nhóm",
        required=False,
        choices=[(q.ma, q.nhan) for q in danh_muc_quyen.DANH_SACH_QUYEN if not q.chi_quan_tri],
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, nhom=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.nhom = nhom
        if nhom is not None:
            self.fields["ma_nhom_quyen"].disabled = True
            self.fields["ma_nhom_quyen"].initial = nhom.ma_nhom_quyen
            self.fields["ten_nhom_quyen"].initial = nhom.ten_nhom_quyen
            self.fields["mo_ta"].initial = nhom.mo_ta
            self.fields["cac_quyen"].initial = list(
                nhom.cac_quyen.values_list("ma_quyen", flat=True)
            )

    def clean_ma_nhom_quyen(self):
        if self.nhom is not None:
            return self.nhom.ma_nhom_quyen
        ma = self.cleaned_data["ma_nhom_quyen"]
        if NhomQuyen.objects.filter(ma_nhom_quyen=ma).exists():
            raise ValidationError("Mã nhóm đã tồn tại.")
        return ma

    def cac_nhom_quyen(self):
        """Quyền gom theo nhóm kèm trạng thái đã chọn, cho template vẽ bảng chọn."""
        chon = set(self["cac_quyen"].value() or [])
        return [
            (nhom, [(q, q.ma in chon) for q in cac_quyen])
            for nhom, cac_quyen in danh_muc_quyen.nhom_theo_module().items()
        ]
