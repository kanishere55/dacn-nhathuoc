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
def so_ngay_toi(ngay, moc):
    """Số ngày từ mốc (thường là hôm nay) tới ngày đã cho; âm khi đã qua."""
    try:
        return (ngay - moc).days
    except TypeError:
        return ""


@register.filter
def thuoc_tinh(doi_tuong, ten):
    """Lấy thuộc tính theo tên cho bảng có cột cấu hình từ view."""
    return getattr(doi_tuong, ten, "")


@register.filter
def tien(gia_tri):
    """12000 → 12.000 đ"""
    if gia_tri in (None, ""):
        return ""
    return f"{so_nguyen(gia_tri)} đ"


@register.filter
def km(gia_tri):
    """1850 (mét) → 1,9 km; dưới 1 km giữ đơn vị mét."""
    if gia_tri in (None, ""):
        return ""
    met = float(gia_tri)
    if met < 1000:
        return f"{round(met)} m"
    return f"{met / 1000:.1f} km".replace(".", ",")


@register.filter
def phong_phu(noi_dung):
    """Nội dung từ trình soạn thảo: làm sạch lại rồi đánh dấu an toàn."""
    from django.utils.safestring import mark_safe

    from ung_dung.chung.noi_dung_phong_phu import hien_thi

    return mark_safe(hien_thi(noi_dung))  # noqa: S308 - đã làm sạch bằng nh3
