"""Hàm nhỏ dùng chung cho view trò chuyện của hai khu."""


def so_truoc(request):
    """Mốc `?truoc=<id tin>` khi tải tin cũ hơn; giá trị lạ coi như không có."""
    truoc = request.GET.get("truoc", "")
    return int(truoc) if truoc.isascii() and truoc.isdecimal() and len(truoc) <= 18 else None
