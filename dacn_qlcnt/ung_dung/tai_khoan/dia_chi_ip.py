"""Địa chỉ IP của người dùng để giới hạn số lần yêu cầu mã xác thực."""

from ipaddress import ip_address


def lay_dia_chi_ip(request):
    """IP của trình duyệt gửi yêu cầu.

    Chạy trực tiếp: REMOTE_ADDR. Chạy sau đường hầm/proxy trên chính máy này (REMOTE_ADDR là
    127.0.0.1, ví dụ khi mở website ra Internet để nhận webhook thanh toán): lấy địa chỉ cuối
    cùng trong X-Forwarded-For, do proxy cục bộ ghi nên người dùng không giả được.
    """
    tu_xa = (request.META.get("REMOTE_ADDR") or "").strip()
    chuyen_tiep = request.META.get("HTTP_X_FORWARDED_FOR", "")
    try:
        la_noi_bo = ip_address(tu_xa).is_loopback
    except ValueError:
        return None
    if la_noi_bo and chuyen_tiep:
        cuoi = chuyen_tiep.split(",")[-1].strip()
        try:
            return str(ip_address(cuoi))
        except ValueError:
            return tu_xa
    return tu_xa
