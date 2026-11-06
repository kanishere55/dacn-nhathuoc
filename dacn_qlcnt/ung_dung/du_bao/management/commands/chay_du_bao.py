from django.core.management.base import BaseCommand, CommandError

from ...models import NguonDuLieu
from ...services.thuc_nghiem import chay_thuc_nghiem


class Command(BaseCommand):
    help = "Chạy năm mô hình dự báo từ nguồn đã nạp trong PostgreSQL."

    def add_arguments(self, parser):
        parser.add_argument("--nguon", type=int)

    def handle(self, *args, **options):
        tap_hop = NguonDuLieu.objects.order_by("-pk")
        if options["nguon"] is not None:
            tap_hop = tap_hop.filter(pk=options["nguon"])
        nguon = tap_hop.first()
        if nguon is None:
            raise CommandError("Chưa có nguồn. Chạy nap_pharma_sales trước.")
        try:
            lan = chay_thuc_nghiem(nguon)
        except ValueError as loi:
            raise CommandError(str(loi)) from loi
        self.stdout.write(
            self.style.SUCCESS(f"Đã ghi lần {lan.pk}: 5 mô hình × 8 nhóm ATC, MAE/RMSE.")
        )
