"""Gọi cổng MoMo API v2 (captureWallet) và kiểm chữ ký HMAC-SHA256.

Tài liệu: https://developers.momo.vn/v3/docs/payment/api/wallet/onetime
Cấu hình trong .env: MOMO_PARTNER_CODE, MOMO_ACCESS_KEY, MOMO_SECRET_KEY,
MOMO_ENDPOINT (mặc định môi trường thử https://test-payment.momo.vn).
"""

import hashlib
import hmac
import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError

TRUONG_KY_KET_QUA = (
    "accessKey",
    "amount",
    "extraData",
    "message",
    "orderId",
    "orderInfo",
    "orderType",
    "partnerCode",
    "payType",
    "requestId",
    "responseTime",
    "resultCode",
    "transId",
)


def da_cau_hinh():
    return all((settings.MOMO_PARTNER_CODE, settings.MOMO_ACCESS_KEY, settings.MOMO_SECRET_KEY))


def ky(cac_cap):
    chuoi = "&".join(f"{ten}={gia_tri}" for ten, gia_tri in cac_cap)
    return hmac.new(settings.MOMO_SECRET_KEY.encode(), chuoi.encode(), hashlib.sha256).hexdigest()


def _goi(duong_dan, than):
    yeu_cau = Request(
        f"{settings.MOMO_ENDPOINT}{duong_dan}",
        data=json.dumps(than).encode(),
        headers={"Content-Type": "application/json; charset=UTF-8"},
        method="POST",
    )
    try:
        with urlopen(yeu_cau, timeout=15) as phan_hoi:
            return json.load(phan_hoi)
    except (URLError, TimeoutError, ValueError) as loi:
        raise ValidationError("Chưa kết nối được MoMo, vui lòng thử lại.") from loi


def tao_thanh_toan(ma_giao_dich, so_tien, mo_ta, url_quay_ve, url_ipn):
    """Trả payUrl để chuyển khách sang trang thanh toán MoMo."""
    than = {
        "partnerCode": settings.MOMO_PARTNER_CODE,
        "requestId": ma_giao_dich,
        "amount": int(so_tien),
        "orderId": ma_giao_dich,
        "orderInfo": mo_ta,
        "redirectUrl": url_quay_ve,
        "ipnUrl": url_ipn,
        "requestType": "captureWallet",
        "extraData": "",
        "lang": "vi",
    }
    than["signature"] = ky(
        [
            ("accessKey", settings.MOMO_ACCESS_KEY),
            ("amount", than["amount"]),
            ("extraData", ""),
            ("ipnUrl", url_ipn),
            ("orderId", ma_giao_dich),
            ("orderInfo", mo_ta),
            ("partnerCode", settings.MOMO_PARTNER_CODE),
            ("redirectUrl", url_quay_ve),
            ("requestId", ma_giao_dich),
            ("requestType", "captureWallet"),
        ]
    )
    ket_qua = _goi("/v2/gateway/api/create", than)
    if ket_qua.get("resultCode") != 0 or not ket_qua.get("payUrl"):
        raise ValidationError(f"MoMo từ chối tạo thanh toán: {ket_qua.get('message', 'không rõ')}")
    return ket_qua["payUrl"]


def kiem_chu_ky_ket_qua(du_lieu):
    """Kiểm chữ ký của IPN hoặc tham số trang quay về."""
    cac_cap = [
        ("accessKey", settings.MOMO_ACCESS_KEY),
        *[(ten, du_lieu.get(ten, "")) for ten in TRUONG_KY_KET_QUA[1:]],
    ]
    return hmac.compare_digest(ky(cac_cap), str(du_lieu.get("signature", "")))


def truy_van(ma_giao_dich):
    """Hỏi trạng thái giao dịch, dùng khi IPN không tới được máy chủ chạy cục bộ."""
    than = {
        "partnerCode": settings.MOMO_PARTNER_CODE,
        "requestId": ma_giao_dich,
        "orderId": ma_giao_dich,
        "lang": "vi",
    }
    than["signature"] = ky(
        [
            ("accessKey", settings.MOMO_ACCESS_KEY),
            ("orderId", ma_giao_dich),
            ("partnerCode", settings.MOMO_PARTNER_CODE),
            ("requestId", ma_giao_dich),
        ]
    )
    return _goi("/v2/gateway/api/query", than)
