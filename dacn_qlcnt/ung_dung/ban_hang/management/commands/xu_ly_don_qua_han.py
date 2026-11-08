from django.core.management.base import BaseCommand

from ung_dung.ban_hang.services.don_hang import xu_ly_qua_han


class Command(BaseCommand):
    help = (
        "Đổi trạng thái đơn quá hạn: giữ tại quầy quá 24 giờ, chờ thanh toán quá 30 phút, "
        "chờ xác nhận quá 24 giờ. Lên lịch chạy mỗi 5 phút bằng Task Scheduler hoặc cron."
    )

    def handle(self, *args, **options):
        self.stdout.write(f"Đã xử lý {xu_ly_qua_han()} đơn quá hạn.")
