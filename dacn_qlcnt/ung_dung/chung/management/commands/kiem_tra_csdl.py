from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from ...kiem_tra_csdl import kiem_tra_csdl


class Command(BaseCommand):
    help = "Đối chiếu tên, kiểu dữ liệu, CHECK, khóa và index trên schema PostgreSQL đã migrate."

    def handle(self, *args, **options):
        so_bang, cac_loi, cac_canh_bao = kiem_tra_csdl(connection)
        for canh_bao in cac_canh_bao:
            self.stdout.write(self.style.WARNING(f"Cảnh báo · {canh_bao}"))
        if cac_loi:
            raise CommandError("\n".join(f"Lỗi · {loi}" for loi in cac_loi))
        self.stdout.write(
            self.style.SUCCESS(
                f"Đạt kiểm tra CSDL · {so_bang} bảng, 0 lỗi, {len(cac_canh_bao)} cảnh báo."
            )
        )
