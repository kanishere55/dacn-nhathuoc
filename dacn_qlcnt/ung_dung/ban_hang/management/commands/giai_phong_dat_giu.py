from django.core.management.base import BaseCommand

from ung_dung.ban_hang.services.dat_giu import giai_phong_het_han


class Command(BaseCommand):
    help = "Giải phóng các đơn giữ quá 24 giờ; có thể lên lịch bằng hệ điều hành."

    def handle(self, *args, **options):
        self.stdout.write(f"Đã giải phóng {giai_phong_het_han()} đơn hết hạn.")
