"""Phát tín hiệu thời gian thực sau khi tin đã ghi PostgreSQL. Redis chỉ chuyển, không lưu."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.urls import reverse

from .selectors import bieu_dien_tin

NHOM_TOAN_CHUOI = "thong_bao.toan_chuoi"
nhat_ky = logging.getLogger(__name__)


def nhom_phong(phong_id):
    return f"tro_chuyen.{phong_id}"


def nhom_khach(khach_id):
    return f"thong_bao.khach.{khach_id}"


def nhom_chi_nhanh(chi_nhanh_id):
    return f"thong_bao.chi_nhanh.{chi_nhanh_id}"


def nhom_nha_thuoc(chi_nhanh_id):
    """Nơi nhận tín hiệu phía nhà thuốc: nhân sự chi nhánh và người xem toàn chuỗi."""
    return [nhom_chi_nhanh(chi_nhanh_id), NHOM_TOAN_CHUOI]


def thong_bao_tin_moi(nguoi, phong, tin):
    """Nội dung thông báo và các nhóm phía người nhận của một tin vừa lưu."""
    tu_khach = nguoi.pk == phong.khach_hang_id
    thong_bao = {
        "ma_phong": phong.pk,
        "tu_khach": tu_khach,
        "tieu_de": (
            nguoi.ho_ten or nguoi.ten_dang_nhap
            if tu_khach
            else f"Nhà thuốc {phong.chi_nhanh.ten_chi_nhanh}"
        ),
        "xem_truoc": tin.noi_dung_tin_nhan[:90],
        "url_khach": reverse("tro_chuyen:khach_chi_tiet", args=[phong.pk]),
        "url_nha_thuoc": reverse("tro_chuyen:chi_tiet", args=[phong.pk]),
    }
    nhom = nhom_nha_thuoc(phong.chi_nhanh_id) if tu_khach else [nhom_khach(phong.khach_hang_id)]
    return thong_bao, nhom


def phat_sau_khi_luu(nguoi, phong, tin):
    """Dùng cho tin lưu qua HTTP (câu hỏi đầu ở form): phát sau khi transaction commit."""
    du_lieu_tin = bieu_dien_tin(tin, phong.khach_hang_id)
    thong_bao, nhom = thong_bao_tin_moi(nguoi, phong, tin)

    def phat():
        kenh = get_channel_layer()
        try:
            async_to_sync(kenh.group_send)(
                nhom_phong(phong.pk), {"type": "phat_tin", "tin": du_lieu_tin}
            )
            for ten_nhom in nhom:
                async_to_sync(kenh.group_send)(
                    ten_nhom, {"type": "tin_moi", "thong_bao": thong_bao}
                )
        except Exception:  # noqa: BLE001 - Redis tắt không được làm hỏng việc lưu tin
            nhat_ky.warning("Không phát được tín hiệu tin mới qua Redis.", exc_info=True)

    transaction.on_commit(phat)
