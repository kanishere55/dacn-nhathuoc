"""Kiểm tra cấu hình gửi email: kết nối, mã hóa, đăng nhập Gmail; tùy chọn gửi một thư thử.

    python manage.py kiem_tra_email
    python manage.py kiem_tra_email --gui-toi ban@example.com

Không in mật khẩu. Lỗi được giải thích bằng tiếng Việt kèm cách sửa.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.management.base import BaseCommand, CommandError

from ung_dung.thong_bao.services import dia_chi_gui
from ung_dung.thong_bao.smtp import giai_thich_loi


class Command(BaseCommand):
    help = "Kiểm tra đăng nhập SMTP và (tùy chọn) gửi một email thử."

    def add_arguments(self, parser):
        parser.add_argument("--gui-toi", help="Địa chỉ nhận thư thử.")

    def handle(self, *args, **tuy_chon):
        if "console" in settings.EMAIL_BACKEND:
            raise CommandError(
                "Chưa cấu hình gửi email: điền EMAIL_HOST_USER và EMAIL_HOST_PASSWORD (mật khẩu "
                "ứng dụng 16 ký tự của Gmail) trong .env. Hiện email chỉ được in ra console."
            )
        self.stdout.write(
            f"Máy chủ {settings.EMAIL_HOST}:{settings.EMAIL_PORT} "
            f"({'SSL' if settings.EMAIL_USE_SSL else 'TLS' if settings.EMAIL_USE_TLS else 'không mã hóa'}), "
            f"tài khoản {settings.EMAIL_HOST_USER}, "
            f"mật khẩu {len(settings.EMAIL_HOST_PASSWORD)} ký tự."
        )
        ket_noi = get_connection()
        try:
            ket_noi.open()
        except Exception as loi:
            raise CommandError(
                f"{giai_thich_loi(loi)}\nChi tiết: {type(loi).__name__}: {loi}"
            ) from loi
        self.stdout.write(self.style.SUCCESS("Đăng nhập máy chủ thư thành công."))
        try:
            if tuy_chon.get("gui_toi"):
                thu = EmailMultiAlternatives(
                    subject="Thư thử cấu hình email",
                    body="Nếu bạn nhận được thư này, website đã gửi email được.",
                    from_email=dia_chi_gui(),
                    to=[tuy_chon["gui_toi"]],
                    connection=ket_noi,
                )
                try:
                    thu.send(fail_silently=False)
                except Exception as loi:
                    raise CommandError(
                        f"{giai_thich_loi(loi)}\nChi tiết: {type(loi).__name__}: {loi}"
                    ) from loi
                self.stdout.write(self.style.SUCCESS(f"Đã gửi thư thử tới {tuy_chon['gui_toi']}."))
        finally:
            ket_noi.close()
