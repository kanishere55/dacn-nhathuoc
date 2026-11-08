"""Bộ lọc định dạng hiển thị theo thói quen Việt Nam; nạp sẵn cho mọi template."""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def so_nguyen(gia_tri):
    """12000 → 12.000"""
    try:
        so = int(Decimal(str(gia_tri)).to_integral_value())
    except (InvalidOperation, ValueError, TypeError):
        return gia_tri
    return f"{so:,}".replace(",", ".")


@register.filter
def tien(gia_tri):
    """12000 → 12.000 đ"""
    if gia_tri in (None, ""):
        return ""
    return f"{so_nguyen(gia_tri)} đ"
