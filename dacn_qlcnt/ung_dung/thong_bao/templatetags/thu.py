"""Bộ lọc riêng cho mẫu email."""

from django import template

from ung_dung.chung.templatetags.dinh_dang import tien

register = template.Library()


@register.filter
def rong_nut(nhan):
    """Bề rộng (px) của nút vẽ bằng VML cho Outlook trên Windows: VML không tự co theo chữ."""
    return max(180, min(360, 56 + 9 * len(str(nhan))))


@register.filter
def tien_lien(gia_tri):
    """Như `tien` nhưng số và chữ "đ" không bị tách xuống hai dòng trên màn hình hẹp."""
    return tien(gia_tri).replace(" ", "\u00a0")
