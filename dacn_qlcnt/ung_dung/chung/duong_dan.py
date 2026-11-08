from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def la_duong_dan_noi_bo(request, duong_dan):
    return bool(duong_dan) and url_has_allowed_host_and_scheme(
        duong_dan, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )


def quay_lai(request, mac_dinh, *args, **kwargs):
    """Chuyển về `next` nếu là đường dẫn cùng website, nếu không về trang mặc định."""
    duong_dan = request.POST.get("next") or request.GET.get("next", "")
    if la_duong_dan_noi_bo(request, duong_dan):
        return redirect(duong_dan)
    return redirect(mac_dinh, *args, **kwargs)
