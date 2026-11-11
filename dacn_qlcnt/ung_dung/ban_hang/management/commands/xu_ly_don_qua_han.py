from django.core.management.base import BaseCommand
from django.utils import timezone

from ung_dung.ban_hang.services.don_hang import xu_ly_qua_han
from ung_dung.thong_bao.models import NhatKyEmail
from ung_dung.thong_bao.services import gui_dong_bo


class Command(BaseCommand):
    help = (
        "Đổi trạng thái đơn quá hạn: giữ tại quầy quá 24 giờ, chờ thanh toán quá 30 phút, "
        "chờ xác nhận quá 24 giờ. "
        "Thư báo khách được gửi xong trước khi lệnh kết thúc. "
        "Lên lịch chạy mỗi 5 phút bằng Task Scheduler hoặc cron."
    )

    def handle(self, *args, **options):
        bat_dau = timezone.now()
        # Gửi đồng bộ: tiến trình lệnh thoát ngay sau khi xử lý, thư gửi nền sẽ bị bỏ dở.
        with gui_dong_bo():
            so_don = xu_ly_qua_han()
        cac_thu = NhatKyEmail.objects.filter(thoi_diem_tao__gte=bat_dau)
        self.stdout.write(
            f"Đã xử lý {so_don} đơn quá hạn. "
            f"Thư báo khách: {cac_thu.filter(trang_thai='da_gui').count()} đã gửi, "
            f"{cac_thu.filter(trang_thai='loi').count()} lỗi."
        )
