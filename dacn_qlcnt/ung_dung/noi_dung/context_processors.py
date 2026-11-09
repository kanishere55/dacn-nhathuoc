from django.utils.functional import SimpleLazyObject

from .selectors import thong_tin_cua_hang, trang_cong_khai


def website(request):
    """Thông tin cửa hàng và trang chính sách cho đầu/chân trang; chỉ truy vấn khi template dùng."""
    return {
        "cua_hang": SimpleLazyObject(thong_tin_cua_hang),
        "trang_chan": SimpleLazyObject(lambda: list(trang_cong_khai())),
    }
