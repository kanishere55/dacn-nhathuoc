"""Đọc thẻ đính kèm (sản phẩm / đơn hàng) gửi lên từ trình duyệt.

Trình duyệt chỉ gửi id; quyền xem đơn và việc đơn thuộc đúng cuộc trò chuyện được kiểm ở
services.kiem_tra_the. Giá trị lạ bị từ chối bằng thông báo tiếng Việt thay vì lỗi 500.
"""

from django.core.exceptions import ValidationError


def _so_id(gia_tri):
    if gia_tri in (None, ""):
        return None
    if isinstance(gia_tri, bool):
        raise ValidationError("Thẻ đính kèm không hợp lệ.")
    if isinstance(gia_tri, int):
        so = gia_tri
    elif (
        isinstance(gia_tri, str) and gia_tri.isascii() and gia_tri.isdecimal() and len(gia_tri) < 19
    ):
        so = int(gia_tri)
    else:
        raise ValidationError("Thẻ đính kèm không hợp lệ.")
    if so <= 0:
        raise ValidationError("Thẻ đính kèm không hợp lệ.")
    return so


def doc_the(id_thuoc, id_don):
    """Trả (thuốc, đơn), mỗi thứ có thể None."""
    from ung_dung.ban_hang.models import DonHang
    from ung_dung.danh_muc.models import Thuoc

    id_thuoc, id_don = _so_id(id_thuoc), _so_id(id_don)
    thuoc = don = None
    if id_thuoc is not None:
        thuoc = Thuoc.objects.filter(pk=id_thuoc).first()
        if thuoc is None:
            raise ValidationError("Sản phẩm đính kèm không còn tồn tại.")
    if id_don is not None:
        don = DonHang.objects.filter(pk=id_don).first()
        if don is None:
            raise ValidationError("Đơn hàng đính kèm không tồn tại.")
    return thuoc, don
