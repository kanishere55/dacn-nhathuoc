"""Trường form dùng chung: chuẩn hóa dữ liệu khớp ràng buộc CSDL trước khi lưu."""

import re

from django import forms
from django.core.exceptions import ValidationError

from .ten_csdl import EMAIL, SO_DIEN_THOAI
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


class TruongEmail(forms.EmailField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 254)
        super().__init__(*args, **kwargs)
        self.widget.attrs.setdefault("autocomplete", "email")

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return value
        value = cat_khoang_trang(value).lower()
        if not re.fullmatch(EMAIL, value):
            raise ValidationError("Email chỉ gồm chữ không dấu, số và các ký tự . _ % + -.")
        return value


class TruongSoDienThoai(forms.CharField):
    """Nhận 0901 234 567, 0901.234.567 hoặc +84901234567; lưu dạng 0901234567."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 20)
        super().__init__(*args, **kwargs)
        self.widget.attrs.update({"inputmode": "tel", "autocomplete": "tel"})

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return ""
        so = re.sub(r"[\s.\-()]", "", value)
        if so.startswith("+84"):
            so = "0" + so[3:]
        elif so.startswith("84") and len(so) in (11, 12):
            so = "0" + so[2:]
        if not re.fullmatch(SO_DIEN_THOAI, so):
            raise ValidationError("Số điện thoại cần 10 chữ số (di động) hoặc 11 chữ số (cố định).")
        return so
