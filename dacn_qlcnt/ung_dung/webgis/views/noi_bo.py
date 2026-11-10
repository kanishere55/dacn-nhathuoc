from django.shortcuts import render
from django.views.decorators.http import require_GET

from ung_dung.chung.permissions import yeu_cau_quyen

from ..selectors import lay_tuy_chon_ban_do_nhiet


@yeu_cau_quyen("ban_do_nhiet.xem")
@require_GET
def ban_do_nhiet(request):
    return render(
        request,
        "webgis/ban_do_nhiet.html",
        {"ban_do_nhiet": lay_tuy_chon_ban_do_nhiet()},
    )
