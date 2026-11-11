"""Gửi email hệ thống: ghi nhật ký trong transaction, gửi SMTP sau khi commit.

Mỗi thư lưu cả bản văn bản thuần lẫn bản HTML (mã OTP đã che) để quản trị xem lại và gửi
lại khi máy chủ thư lỗi. Thư gửi trong luồng riêng để trang web không chờ máy chủ thư;
luồng KHÔNG phải daemon nên tiến trình ngắn (lệnh định kỳ, tắt server) chờ gửi xong rồi mới
thoát. Lệnh quản trị gửi đồng bộ bằng `with gui_dong_bo():` để in được kết quả.
"""

import contextvars
import logging
import threading
from contextlib import contextmanager
from datetime import timedelta
from email.utils import formataddr

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db import close_old_connections, transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from ung_dung.chung.van_ban import cat_khoang_trang

from .models import LOAI_KHONG_GUI_LAI, SO_LAN_GUI_TOI_DA, NhatKyEmail
from .smtp import giai_thich_loi

nhat_ky = logging.getLogger(__name__)

# Thư "Chờ gửi" lâu hơn chừng này coi như bị kẹt (tiến trình gửi đã dừng).
PHUT_COI_LA_KET = 10
SO_TRANG_CHINH_SACH_TRONG_THU = 6

_GUI_DONG_BO = contextvars.ContextVar("gui_email_dong_bo", default=False)
_CAC_LUONG = set()
_KHOA_CAC_LUONG = threading.Lock()

LY_DO_NHAN = {
    "don_hang": "Bạn nhận thư này vì đã đặt đơn tại {ten}.",
    "tai_khoan": "Bạn nhận thư này vì email này gắn với một tài khoản tại {ten}.",
}


def url_tuyet_doi(ten_url, *args):
    """Đường dẫn mở được từ hộp thư: URL_WEBSITE (cấu hình .env) ghép với reverse()."""
    return settings.URL_WEBSITE + reverse(ten_url, args=args)


def ten_thuong_hieu():
    from ung_dung.noi_dung.selectors import thong_tin_cua_hang

    return thong_tin_cua_hang().ten_thuong_hieu


def ngu_canh_chung():
    """Thông tin cửa hàng lấy từ CSDL cho đầu thư, chân thư và khối liên hệ."""
    from ung_dung.noi_dung.selectors import thong_tin_cua_hang, trang_cong_khai

    cua_hang = thong_tin_cua_hang()
    return {
        "cua_hang": cua_hang,
        "ten_thuong_hieu": cua_hang.ten_thuong_hieu,
        "url_website": settings.URL_WEBSITE,
        "url_trang_chu": url_tuyet_doi("chung:trang_chu"),
        "url_quen_mat_khau": url_tuyet_doi("tai_khoan:quen_mat_khau"),
        "cac_trang_chinh_sach": [
            {
                "tieu_de": trang.tieu_de,
                "url": url_tuyet_doi("noi_dung:trang", trang.duong_dan_trang),
            }
            for trang in trang_cong_khai().order_by("thu_tu", "pk")[:SO_TRANG_CHINH_SACH_TRONG_THU]
        ],
    }


def mot_dong(van_ban, gioi_han=500):
    """Gộp mọi khoảng trắng, kể cả xuống dòng Unicode, để lưu vào cột một dòng."""
    return cat_khoang_trang(" ".join(str(van_ban).split()))[:gioi_han] or "Lỗi không rõ"


def dia_chi_gui():
    """Người gửi: DEFAULT_FROM_EMAIL trong .env, không có thì tên thương hiệu lưu trong CSDL."""
    if settings.EMAIL_HOST_USER and not getattr(settings, "NGUOI_GUI_CO_DINH", False):
        return formataddr((ten_thuong_hieu(), settings.EMAIL_HOST_USER))
    return settings.DEFAULT_FROM_EMAIL


def gui_email(
    *,
    loai_email,
    email_nhan,
    tieu_de,
    mau,
    ngu_canh=None,
    tai_khoan=None,
    don_hang=None,
    dinh_kem_hoa_don=False,
    tom_tat="",
    ly_do_nhan="",
    gui_ngay=False,
):
    """Tạo nhật ký và hẹn gửi khi transaction hiện tại commit.

    `mau` là tên mẫu trong thong_bao/email/ (không đuôi), có bản .html và .txt. Mẫu nhận
    biến `an_bi_mat`: bản lưu vào CSDL được dựng với an_bi_mat=True để che mã OTP.
    `tom_tat`: một câu hiện ở dòng xem trước của hộp thư (preheader).
    `don_hang`: đơn liên quan, để giới hạn nhật ký theo chi nhánh và dựng lại hóa đơn.
    `dinh_kem_hoa_don`: kèm hóa đơn bán lẻ PDF; tệp dựng sau commit, lúc gửi, không lưu.
    `gui_ngay`: gửi trong luồng của yêu cầu ngay sau commit (mã OTP) để trang báo được cho
    người dùng khi gửi lỗi, thay vì nói "đã gửi" trong khi thư không đi.
    """
    chung = ngu_canh_chung()
    ngu_canh = {
        **chung,
        **(ngu_canh or {}),
        "tieu_de": tieu_de,
        "tom_tat": tom_tat or tieu_de,
        "ly_do_nhan": ly_do_nhan
        or LY_DO_NHAN["don_hang" if don_hang else "tai_khoan"].format(ten=chung["ten_thuong_hieu"]),
    }
    van_ban = render_to_string(f"thong_bao/email/{mau}.txt", ngu_canh)
    html = render_to_string(f"thong_bao/email/{mau}.html", ngu_canh)
    if loai_email in LOAI_KHONG_GUI_LAI:
        che = {**ngu_canh, "an_bi_mat": True}
        if loai_email == "email_da_doi":
            che.update(url_hoan_tac="", nut_chinh=None)
        ban_luu, html_luu = (
            render_to_string(f"thong_bao/email/{mau}.txt", che),
            render_to_string(f"thong_bao/email/{mau}.html", che),
        )
    else:
        ban_luu, html_luu = van_ban, html
    ban_ghi = NhatKyEmail.objects.create(
        loai_email=loai_email,
        email_nhan=email_nhan,
        tai_khoan=tai_khoan,
        don_hang=don_hang,
        co_dinh_kem_hoa_don=bool(dinh_kem_hoa_don and don_hang),
        tieu_de=tieu_de,
        noi_dung_van_ban=cat_khoang_trang(ban_luu),
        noi_dung_html=html_luu.strip(),
    )
    goi = _goi(ban_ghi, van_ban=van_ban, html=html)
    transaction.on_commit(lambda: _bat_dau_gui(goi, gui_ngay))
    return ban_ghi


def _goi(ban_ghi, *, van_ban, html):
    from ung_dung.noi_dung.selectors import thong_tin_cua_hang

    tra_loi = thong_tin_cua_hang().email_lien_he
    return {
        "id_nhat_ky": ban_ghi.pk,
        "so_lan_gui": ban_ghi.so_lan_gui,
        "email_nhan": ban_ghi.email_nhan,
        "tieu_de": ban_ghi.tieu_de,
        "van_ban": van_ban,
        "html": html,
        "id_don_hang": ban_ghi.don_hang_id,
        "dinh_kem_hoa_don": ban_ghi.co_dinh_kem_hoa_don,
        "nguoi_gui": dia_chi_gui(),
        # Khách bấm Trả lời thì thư tới hộp thư có người đọc, không phải địa chỉ gửi tự động.
        "tra_loi": [tra_loi] if tra_loi else [],
    }


@contextmanager
def gui_dong_bo():
    """Trong khối này mọi thư được gửi ngay trong luồng hiện tại khi transaction commit.

    Dùng cho lệnh quản trị: lệnh kết thúc là thư đã gửi xong (hoặc đã ghi lỗi).
    """
    dau = _GUI_DONG_BO.set(True)
    try:
        yield
    finally:
        _GUI_DONG_BO.reset(dau)


def cho_gui_xong(thoi_gian_cho=None):
    """Chờ các luồng gửi nền đang chạy kết thúc; trả số luồng còn chưa xong."""
    with _KHOA_CAC_LUONG:
        cac_luong = list(_CAC_LUONG)
    for luong in cac_luong:
        luong.join(thoi_gian_cho)
    return sum(luong.is_alive() for luong in cac_luong)


def _gui_nen_duoc():
    # Backend locmem chỉ dùng khi chạy test: gửi ngay để test đọc được mail.outbox.
    return (
        settings.EMAIL_GUI_NEN and "locmem" not in settings.EMAIL_BACKEND and not _GUI_DONG_BO.get()
    )


def _bat_dau_gui(goi, gui_ngay=False):
    if gui_ngay or not _gui_nen_duoc():
        _gui(goi)
        return
    luong = threading.Thread(
        target=_gui_trong_luong_rieng,
        args=(goi,),
        # Không phải daemon: Python chờ luồng này xong mới thoát tiến trình.
        daemon=False,
        name=f"gui-email-{goi['id_nhat_ky']}",
    )
    with _KHOA_CAC_LUONG:
        _CAC_LUONG.add(luong)
    luong.start()


def _gui_trong_luong_rieng(goi):
    try:
        _gui(goi)
    finally:
        close_old_connections()
        with _KHOA_CAC_LUONG:
            _CAC_LUONG.discard(threading.current_thread())


def _tep_dinh_kem(goi):
    """Dựng hóa đơn PDF lúc gửi (sau commit, ngoài khóa kho). Lỗi thì gửi thư không kèm tệp:
    thư vẫn có nút tải hóa đơn trên website."""
    if not goi.get("dinh_kem_hoa_don") or not goi.get("id_don_hang"):
        return []
    from ung_dung.ban_hang.services.thong_bao_don import tep_hoa_don

    try:
        tep = tep_hoa_don(goi["id_don_hang"])
    except Exception as loi:  # Thiếu font, lỗi dữ liệu... không được làm mất thư.
        nhat_ky.warning("Dựng hóa đơn đính kèm thư %s lỗi: %s", goi["id_nhat_ky"], loi)
        tep = None
    if tep is None:
        NhatKyEmail.objects.filter(pk=goi["id_nhat_ky"]).update(co_dinh_kem_hoa_don=False)
        return []
    return [tep]


def _gui(goi):
    ban_ghi = NhatKyEmail.objects.filter(
        pk=goi["id_nhat_ky"], so_lan_gui=goi["so_lan_gui"], trang_thai="cho_gui"
    )
    if not ban_ghi.exists():
        return
    thu = EmailMultiAlternatives(
        subject=goi["tieu_de"],
        body=goi["van_ban"],
        from_email=goi.get("nguoi_gui") or settings.DEFAULT_FROM_EMAIL,
        to=[goi["email_nhan"]],
        reply_to=goi.get("tra_loi") or None,
        # RFC 3834: thư tự động, máy chủ nhận không gửi thư trả lời tự động (vắng mặt...).
        headers={"Auto-Submitted": "auto-generated"},
    )
    thu.attach_alternative(goi["html"], "text/html")
    try:
        for ten, du_lieu, kieu in _tep_dinh_kem(goi):
            thu.attach(ten, du_lieu, kieu)
        if not thu.send(fail_silently=False):
            raise OSError("Máy chủ thư không xác nhận nhận thư.")
    except Exception as loi:  # SMTP có thể lỗi mạng, xác thực hoặc từ chối người nhận.
        nhat_ky.warning("Gửi email %s lỗi: %s", goi["id_nhat_ky"], loi)
        ban_ghi.update(
            trang_thai="loi",
            chi_tiet_loi=mot_dong(f"{giai_thich_loi(loi)} Chi tiết: {type(loi).__name__}: {loi}"),
        )
    else:
        ban_ghi.update(trang_thai="da_gui", thoi_diem_gui=timezone.now())


# Gửi lại


def dieu_kien_can_gui_lai():
    """Thư gửi lỗi, hoặc "Chờ gửi" quá PHUT_COI_LA_KET phút (tiến trình gửi đã dừng)."""
    moc = timezone.now() - timedelta(minutes=PHUT_COI_LA_KET)
    return Q(trang_thai="loi") | (
        Q(trang_thai="cho_gui")
        & (Q(thoi_diem_thu_lai__lt=moc) | Q(thoi_diem_thu_lai__isnull=True, thoi_diem_tao__lt=moc))
    )


def thu_gui_lai_duoc():
    """Thư cần gửi lại mà hệ thống gửi lại được (có bản HTML, không phải mã OTP, chưa quá lượt)."""
    return (
        NhatKyEmail.objects.filter(dieu_kien_can_gui_lai())
        .filter(noi_dung_html__isnull=False, so_lan_gui__lt=SO_LAN_GUI_TOI_DA)
        .exclude(loai_email__in=LOAI_KHONG_GUI_LAI)
        .order_by("thoi_diem_tao", "pk")
    )


def ly_do_khong_gui_lai(ban_ghi):
    """Câu giải thích vì sao thư không gửi lại được lúc này; rỗng khi gửi lại được."""
    if ban_ghi.trang_thai == "da_gui":
        return "Thư đã gửi thành công, không cần gửi lại."
    if ban_ghi.trang_thai == "cho_gui" and (
        ban_ghi.thoi_diem_thu_lai or ban_ghi.thoi_diem_tao
    ) >= timezone.now() - timedelta(minutes=PHUT_COI_LA_KET):
        return "Thư đang trong hàng chờ gửi. Đợi vài phút rồi xem lại."
    return ban_ghi.ly_do_khong_gui_lai


def _gui_lai(id_nhat_ky):
    """Gửi lại một thư từ bản đã lưu, đồng bộ để báo ngay kết quả. Trả bản ghi sau khi gửi."""
    with transaction.atomic():
        ban_ghi = NhatKyEmail.objects.select_for_update().get(pk=id_nhat_ky)
        ly_do = ly_do_khong_gui_lai(ban_ghi)
        if ly_do:
            raise ValidationError(ly_do)
        ban_ghi.trang_thai = "cho_gui"
        ban_ghi.chi_tiet_loi = ""
        ban_ghi.so_lan_gui += 1
        ban_ghi.thoi_diem_thu_lai = timezone.now()
        ban_ghi.save(
            update_fields=["trang_thai", "chi_tiet_loi", "so_lan_gui", "thoi_diem_thu_lai"]
        )
        goi = _goi(ban_ghi, van_ban=ban_ghi.noi_dung_van_ban, html=ban_ghi.noi_dung_html)
    _gui(goi)
    ban_ghi.refresh_from_db()
    return ban_ghi


def gui_lai(nguoi, nhat_ky):
    """Người xem nhật ký bấm "Gửi lại" cho thư lỗi hoặc kẹt trong phạm vi được xem."""
    from .selectors import lay_nhat_ky_email

    if not lay_nhat_ky_email(nguoi).filter(pk=nhat_ky.pk).exists():
        raise PermissionDenied("Thư không thuộc phạm vi bạn được xem.")
    return _gui_lai(nhat_ky.pk)


def gui_lai_thu_ton(toi_da=50):
    """Lệnh định kỳ: gửi lại các thư lỗi/kẹt gửi lại được. Trả (số đã gửi, số còn lỗi)."""
    da_gui = con_loi = 0
    for ma in list(thu_gui_lai_duoc().values_list("pk", flat=True)[:toi_da]):
        try:
            ban_ghi = _gui_lai(ma)
        except ValidationError:
            continue  # vừa được người khác gửi lại
        if ban_ghi.trang_thai == "da_gui":
            da_gui += 1
        else:
            con_loi += 1
    return da_gui, con_loi
