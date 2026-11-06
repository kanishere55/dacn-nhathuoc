from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from ...services.nhap_du_lieu import nap_salesdaily


class Command(BaseCommand):
    help = "Nạp salesdaily.csv (ngoài project) vào PostgreSQL, kiểm nguồn bằng SHA-256."

    def add_arguments(self, parser):
        parser.add_argument("duong_dan")
        parser.add_argument("--ten-nguon", default="Pharma Sales Data · Milan Zdravković")

    def handle(self, *args, **options):
        try:
            nguon, da_tao = nap_salesdaily(options["duong_dan"], options["ten_nguon"])
        except (ValidationError, OSError) as loi:
            raise CommandError(str(loi)) from loi
        trang_thai = "Đã nạp" if da_tao else "Đã có"
        self.stdout.write(self.style.SUCCESS(f"{trang_thai} nguồn {nguon.pk} · {nguon.bam_sha256}"))
