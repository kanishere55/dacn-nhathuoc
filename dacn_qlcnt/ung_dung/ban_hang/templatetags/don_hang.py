"""Bộ lọc hiển thị hạn xử lý đơn trên danh sách và chi tiết đơn."""

from django import template

from ..selectors import thong_tin_han

register = template.Library()


@register.filter
def han_don(don):
    """Thông tin hạn của đơn đang giữ hàng ({chu, muc, hau_qua}) hoặc None."""
    return thong_tin_han(don)
