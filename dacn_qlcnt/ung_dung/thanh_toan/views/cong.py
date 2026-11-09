"""Điểm nhận thông báo từ cổng thanh toán (máy chủ gọi máy chủ, không có phiên đăng nhập)."""

import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .. import momo
from ..services.cong import xu_ly_ket_qua_momo, xu_ly_sepay

nhat_ky = logging.getLogger(__name__)


def _doc_json(request):
    try:
        du_lieu = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return None
    return du_lieu if isinstance(du_lieu, dict) else None


@csrf_exempt
@require_POST
def sepay_webhook(request):
    khoa = settings.SEPAY_API_KEY
    tieu_de = request.headers.get("Authorization", "")
    if not khoa or not hmac.compare_digest(tieu_de, f"Apikey {khoa}"):
        return JsonResponse({"success": False}, status=401)
    du_lieu = _doc_json(request)
    if du_lieu is None:
        return JsonResponse({"success": False}, status=400)
    ket_qua = xu_ly_sepay(du_lieu)
    nhat_ky.info("SePay %s: %s", du_lieu.get("id"), ket_qua)
    return JsonResponse({"success": True, "ket_qua": ket_qua})


@csrf_exempt
@require_POST
def momo_ipn(request):
    du_lieu = _doc_json(request)
    if du_lieu is None or not momo.da_cau_hinh() or not momo.kiem_chu_ky_ket_qua(du_lieu):
        return HttpResponse(status=400)
    nhat_ky.info("MoMo IPN %s: %s", du_lieu.get("orderId"), xu_ly_ket_qua_momo(du_lieu))
    return HttpResponse(status=204)
