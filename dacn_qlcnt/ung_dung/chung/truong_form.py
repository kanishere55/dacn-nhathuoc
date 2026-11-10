"""Trường form dùng chung: chuẩn hóa dữ liệu khớp ràng buộc CSDL trước khi lưu."""

import re

from django import forms
from django.core.exceptions import ValidationError

from .ten_csdl import EMAIL, SO_DI_DONG, SO_HOTLINE
from .van_ban import cat_khoang_trang, la_mot_dong


class TruongMotDong(forms.CharField):
    """Văn bản một dòng, đã cắt khoảng trắng Unicode ở hai đầu."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 255)
        kwargs["strip"] = False
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = cat_khoang_trang(super().to_python(value) or "")
        if not la_mot_dong(value):
            raise ValidationError("Chỉ nhập một dòng, không chứa ký tự điều khiển.")
        return value


class TruongHoTen(TruongMotDong):
    """Họ tên người: chữ cái (có dấu tiếng Việt) và dấu cách, có thể có dấu nháy hoặc gạch nối."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 100)
        kwargs.setdefault("error_messages", {}).setdefault("required", "Vui lòng nhập họ và tên.")
        super().__init__(*args, **kwargs)
        self.widget.attrs.setdefault("autocomplete", "name")
        self.widget.attrs.setdefault("placeholder", "Ví dụ: Nguyễn Văn An")

    def to_python(self, value):
        value = " ".join(super().to_python(value).split())
        if not value:
            return value
        if any(ky_tu.isdigit() for ky_tu in value):
            raise ValidationError("Họ tên không được chứa chữ số.")
        if not re.fullmatch(r"[^\W\d_]+([ '.-][^\W\d_]+)*\.?", value):
            raise ValidationError("Họ tên chỉ gồm chữ cái và dấu cách, ví dụ Nguyễn Văn An.")
        if len(value) < 2:
            raise ValidationError("Họ tên quá ngắn.")
        return value


# Tên miền hay gõ nhầm → tên miền đúng; báo "Có phải ý bạn là…" thay vì lưu email không ai nhận.
TEN_MIEN_GO_NHAM = {
    "gmai.com": "gmail.com",
    "gmial.com": "gmail.com",
    "gamil.com": "gmail.com",
    "gmal.com": "gmail.com",
    "gmaill.com": "gmail.com",
    "gmail.co": "gmail.com",
    "gmail.con": "gmail.com",
    "gmail.cm": "gmail.com",
    "gmail.om": "gmail.com",
    "gmail.vn": "gmail.com",
    "gmail.com.vn": "gmail.com",
    "yahoo.con": "yahoo.com",
    "yaho.com": "yahoo.com",
    "hotmail.con": "hotmail.com",
    "hotmai.com": "hotmail.com",
    "outlook.con": "outlook.com",
    "outlok.com": "outlook.com",
    "icloud.con": "icloud.com",
}


class TruongEmail(forms.EmailField):
    """Email lưu chữ thường; báo lỗi tiếng Việt cụ thể (có dấu, thiếu @, gõ nhầm tên miền)."""

    default_error_messages = {
        "invalid": "Email chưa đúng định dạng. Ví dụ đúng: ten.ban@gmail.com.",
        "required": "Vui lòng nhập email.",
    }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 254)
        super().__init__(*args, **kwargs)
        self.widget.attrs.setdefault("autocomplete", "email")
        self.widget.attrs.setdefault("placeholder", "ten.ban@gmail.com")
        self.widget.attrs.setdefault("inputmode", "email")

    def to_python(self, value):
        value = cat_khoang_trang(super().to_python(value) or "")
        if not value:
            return value
        if " " in value:
            raise ValidationError("Email không được chứa dấu cách.")
        if value.count("@") != 1:
            raise ValidationError("Email phải có đúng một ký tự @, ví dụ ten.ban@gmail.com.")
        if not value.isascii():
            raise ValidationError("Email chỉ gồm chữ không dấu, số và các ký tự . _ % + -.")
        return value.lower()

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return value
        ten, _, mien = value.partition("@")
        if mien in TEN_MIEN_GO_NHAM:
            raise ValidationError(
                f"Tên miền “{mien}” có vẻ bị gõ nhầm. Có phải ý bạn là {ten}@{TEN_MIEN_GO_NHAM[mien]}?"
            )
        if not re.fullmatch(EMAIL, value):
            raise ValidationError(
                "Email chỉ gồm chữ không dấu, số và các ký tự . _ % + -, tên miền phải có dấu "
                "chấm (ví dụ gmail.com)."
            )
        return value


# Thông báo chung cho mọi lỗi số điện thoại: kèm ví dụ để người nhập sửa ngay.
_VI_DU_DI_DONG = "ví dụ 0912 345 678"


class TruongSoDienThoai(forms.CharField):
    """Số điện thoại Việt Nam. Nhận 0901 234 567, 0901.234.567 hoặc +84 901 234 567; lưu 0901234567.

    `loai`: "dien_thoai" (di động hoặc máy bàn), "di_dong" (chỉ di động, ví dụ ví MoMo),
    "hotline" (thêm tổng đài 1800/1900). Quy tắc khớp ràng buộc CSDL ở ten_csdl.py.
    """

    def __init__(self, *args, loai="dien_thoai", **kwargs):
        kwargs.setdefault("max_length", 20)
        kwargs.setdefault("error_messages", {})
        kwargs["error_messages"].setdefault("required", "Vui lòng nhập số điện thoại.")
        kwargs["error_messages"].setdefault(
            "max_length", "Số điện thoại quá dài. Số di động Việt Nam chỉ có 10 chữ số."
        )
        self.loai = loai
        super().__init__(*args, **kwargs)
        self.widget.attrs.update(
            {
                "inputmode": "tel",
                "autocomplete": "tel",
                "placeholder": "Ví dụ: 1900 6035" if loai == "hotline" else "Ví dụ: 0912 345 678",
                # Trình duyệt chặn sớm chữ cái; quy tắc đầu số do máy chủ kiểm.
                # Thoát ( ) - để hợp lệ cả với cờ regex "v" của trình duyệt mới.
                "pattern": r"[0-9+ .\(\)\-]*",
                "title": "Chỉ nhập chữ số, có thể cách bằng dấu cách hoặc dấu chấm.",
            }
        )

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return ""
        so = re.sub(r"[\s.\-()]", "", value)
        if not re.fullmatch(r"\+?[0-9]+", so):
            raise ValidationError(
                "Số điện thoại chỉ gồm chữ số (có thể cách bằng dấu cách hoặc dấu chấm), "
                f"{_VI_DU_DI_DONG}."
            )
        if so.startswith("+84"):
            so = "0" + so[3:]
        elif so.startswith("+"):
            raise ValidationError("Chỉ nhận số điện thoại Việt Nam (đầu +84 hoặc 0).")
        elif so.startswith("84") and len(so) in (11, 12):
            so = "0" + so[2:]
        if self.loai == "hotline" and re.fullmatch(SO_HOTLINE, so):
            return so
        if so.startswith(("1800", "1900")):
            raise ValidationError(
                "Tổng đài 1800/1900 gồm 8 hoặc 10 chữ số."
                if self.loai == "hotline"
                else "Không nhận số tổng đài 1800/1900; hãy nhập số di động hoặc máy bàn."
            )
        if not so.startswith("0"):
            raise ValidationError(
                f"Số điện thoại Việt Nam bắt đầu bằng 0 hoặc +84, {_VI_DU_DI_DONG}."
            )
        if so.startswith("02"):
            if self.loai == "di_dong":
                raise ValidationError(f"Cần số di động, không nhận số máy bàn ({_VI_DU_DI_DONG}).")
            if len(so) != 11:
                raise ValidationError(
                    f"Số máy bàn gồm 11 chữ số: 02 + mã vùng + số máy (bạn nhập {len(so)} số), "
                    "ví dụ 028 3812 3456."
                )
            return so
        if so.startswith("01") and len(so) == 11:
            raise ValidationError(
                "Đầu số 01x (11 số) đã đổi sang đầu số mới từ năm 2018, ví dụ 0168 → 038. "
                "Hãy nhập số mới 10 chữ số."
            )
        if len(so) != 10:
            raise ValidationError(
                f"Số di động gồm 10 chữ số (bạn nhập {len(so)} số), {_VI_DU_DI_DONG}."
            )
        if not re.fullmatch(SO_DI_DONG, so):
            raise ValidationError(
                f"Đầu số {so[:3]} không phải đầu số di động Việt Nam đang dùng "
                "(03x, 05x, 07x, 08x, 09x). Kiểm tra lại số."
            )
        return so


class TrinhSoanThao(forms.Textarea):
    """Ô soạn nội dung có thanh công cụ định dạng (Quill); thiếu JS vẫn dùng như textarea."""

    @property
    def media(self):
        from ung_dung.chung.templatetags.tai_nguyen import tep_tinh

        return forms.Media(
            css={"all": ("vendor/quill/quill.snow.css",)},
            js=("vendor/quill/quill.min.js", tep_tinh("chung/js/trinh_soan_thao.js")),
        )

    def __init__(self, attrs=None):
        super().__init__({"rows": 8, "data-trinh-soan-thao": "", **(attrs or {})})

    def get_context(self, name, value, attrs):
        from django.urls import reverse

        # Đường dẫn tải ảnh lên được tính khi vẽ để không phụ thuộc thứ tự nạp URL.
        attrs = {**(attrs or {}), "data-url-tai-anh": reverse("danh_muc:anh_noi_dung_tai_len")}
        return super().get_context(name, value, attrs)


class TruongPhongPhu(forms.CharField):
    """Nội dung định dạng: làm sạch HTML bằng nh3 trước khi lưu."""

    widget = TrinhSoanThao

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 20000)
        kwargs["strip"] = False
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        from .noi_dung_phong_phu import lam_sach_html

        return lam_sach_html(super().to_python(value) or "")
