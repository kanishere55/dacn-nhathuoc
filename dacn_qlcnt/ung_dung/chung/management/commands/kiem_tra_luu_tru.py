from django.core.checks import run_checks
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Kiểm tra cấu hình và tệp dữ liệu bị cấm theo mục 10 của quy ước project."
    requires_system_checks = []

    def handle(self, *args, **options):
        cac_loi = run_checks(tags=["luu_tru"])
        if cac_loi:
            raise CommandError("\n".join(str(loi) for loi in cac_loi))
        self.stdout.write(self.style.SUCCESS("Đạt kiểm tra cấu hình và các tệp dữ liệu bị cấm."))
