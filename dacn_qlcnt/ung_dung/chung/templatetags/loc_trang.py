from urllib.parse import urlencode

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def truy_van(context, **thay_doi):
    """Chuỗi truy vấn hiện tại với một số tham số đổi hoặc bỏ (giá trị rỗng/None là bỏ)."""
    tham_so = context["request"].GET.copy()
    for ten, gia_tri in thay_doi.items():
        if gia_tri in (None, ""):
            tham_so.pop(ten, None)
        else:
            tham_so[ten] = str(gia_tri)
    chuoi = urlencode(tham_so, doseq=True)
    return "?" + chuoi if chuoi else "?"


@register.filter
def cac_so_trang(trang):
    """Dãy số trang gọn quanh trang hiện tại; None là dấu ba chấm."""
    tong, hien_tai = trang.paginator.num_pages, trang.number
    cac_so = sorted({1, tong, *range(max(1, hien_tai - 2), min(tong, hien_tai + 2) + 1)})
    ket_qua, truoc = [], 0
    for so in cac_so:
        if so - truoc > 1:
            ket_qua.append(None)
        ket_qua.append(so)
        truoc = so
    return ket_qua
