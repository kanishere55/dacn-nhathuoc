"""Gửi email hệ thống: ghi nhật ký trong transaction, gửi SMTP sau khi commit."""

import logging
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import close_old_connections, transaction
from django.template.loader import render_to_string
from django.utils import timezone

from ung_dung.chung.van_ban import cat_khoang_trang

from .models import NhatKyEmail

nhat_ky = logging.getLogger(__name__)


def ngu_canh_chung():
    return {
        "ten_thuong_hieu": settings.TEN_THUONG_HIEU,
        "url_website": settings.URL_WEBSITE,
    }


def mot_dong(van_ban, gioi_han=500):
    """Gộp mọi khoảng trắng, kể cả xuống dòng Unicode, để lưu vào cột một dòng."""
    return cat_khoang_trang(" ".join(str(van_ban).split()))[:gioi_han] or "Lỗi không rõ"


def gui_email(
    *, loai_email, email_nhan, tieu_de, mau, ngu_canh=None, tai_khoan=None, tep_dinh_kem=()
):
    """Tạo nhật ký và hẹn gửi khi transaction hiện tại commit.

    `mau` là tên mẫu trong thong_bao/email/ (không đuôi). Mẫu văn bản nhận biến
    `an_bi_mat`: bản lưu vào CSDL được dựng với an_bi_mat=True để che OTP.
    `tep_dinh_kem`: các bộ (tên tệp, bytes, kiểu MIME); chỉ gửi đi, không lưu CSDL.
    """
    ngu_canh = {**ngu_canh_chung(), **(ngu_canh or {}), "tieu_de": tieu_de}
    van_ban = render_to_string(f"thong_bao/email/{mau}.txt", ngu_canh)
    html = render_to_string(f"thong_bao/email/{mau}.html", ngu_canh)
    ban_luu = render_to_string(f"thong_bao/email/{mau}.txt", {**ngu_canh, "an_bi_mat": True})
    ban_ghi = NhatKyEmail.objects.create(
        loai_email=loai_email,
        email_nhan=email_nhan,
        tai_khoan=tai_khoan,
        tieu_de=tieu_de,
        noi_dung_van_ban=cat_khoang_trang(ban_luu),
    )
    goi = {
        "id_nhat_ky": ban_ghi.pk,
        "email_nhan": email_nhan,
        "tieu_de": tieu_de,
        "van_ban": van_ban,
        "html": html,
        "tep_dinh_kem": list(tep_dinh_kem),
    }
    transaction.on_commit(lambda: _bat_dau_gui(goi))
    return ban_ghi


def _bat_dau_gui(goi):
    # Backend locmem chỉ dùng khi chạy test: gửi ngay để test đọc được mail.outbox.
    if settings.EMAIL_GUI_NEN and "locmem" not in settings.EMAIL_BACKEND:
        threading.Thread(target=_gui_trong_luong_rieng, args=(goi,), daemon=True).start()
    else:
        _gui(goi)


def _gui_trong_luong_rieng(goi):
    try:
        _gui(goi)
    finally:
        close_old_connections()


def _gui(goi):
    thu = EmailMultiAlternatives(
        subject=goi["tieu_de"],
        body=goi["van_ban"],
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[goi["email_nhan"]],
    )
    thu.attach_alternative(goi["html"], "text/html")
    for ten, du_lieu, kieu in goi.get("tep_dinh_kem", ()):
        thu.attach(ten, du_lieu, kieu)
    try:
        thu.send(fail_silently=False)
    except Exception as loi:  # SMTP có thể lỗi mạng, xác thực hoặc từ chối người nhận.
        nhat_ky.warning("Gửi email %s lỗi: %s", goi["id_nhat_ky"], loi)
        NhatKyEmail.objects.filter(pk=goi["id_nhat_ky"]).update(
            trang_thai="loi",
            chi_tiet_loi=mot_dong(f"{type(loi).__name__}: {loi}"),
        )
    else:
        NhatKyEmail.objects.filter(pk=goi["id_nhat_ky"]).update(
            trang_thai="da_gui", thoi_diem_gui=timezone.now()
        )
