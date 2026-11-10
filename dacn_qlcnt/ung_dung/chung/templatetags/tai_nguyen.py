from pathlib import Path

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def url_css_giao_dien():
    ten_tep = "css/da_bien_dich.css"
    url = static(ten_tep)
    tep = Path(finders.find(ten_tep) or Path(settings.STATIC_ROOT, ten_tep))
    try:
        phien_ban = tep.stat().st_mtime_ns
    except FileNotFoundError:
        return url
    return f"{url}?v={phien_ban:x}"


@register.simple_tag
def tep_tinh(ten_tep):
    """Như {% static %} nhưng thêm ?v=thời điểm sửa tệp, tránh trình duyệt dùng JS/CSS cũ."""
    url = static(ten_tep)
    tep = finders.find(ten_tep)
    if not tep:
        return url
    return f"{url}?v={Path(tep).stat().st_mtime_ns:x}"
