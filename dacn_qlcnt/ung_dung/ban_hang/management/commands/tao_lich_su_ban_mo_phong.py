from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError

from ...services.lich_su_mo_phong import tao_lich_su_ban_mo_phong


class Command(BaseCommand):
    help = "Sinh lịch sử bán tại quầy nhiều ngày cho dữ liệu mô phỏng, qua nghiệp vụ thật."

    def add_arguments(self, parser):
        parser.add_argument(
            "--quan-tri", required=True, help="Tên tài khoản quản trị chuỗi đang hoạt động."
        )
        parser.add_argument("--so-ngay", type=int, default=60, help="Số ngày lùi về trước.")
        parser.add_argument("--hat-giong", type=int, default=2026, help="Hạt giống ngẫu nhiên.")

    def handle(self, *args, **options):
        quan_tri = get_user_model().objects.filter(ten_dang_nhap=options["quan_tri"]).first()
        if quan_tri is None:
            raise CommandError("Không tìm thấy tài khoản quản trị.")
        try:
            ket_qua = tao_lich_su_ban_mo_phong(
                quan_tri, so_ngay=options["so_ngay"], hat_giong=options["hat_giong"]
            )
        except (PermissionDenied, ValidationError) as loi:
            raise CommandError(" ".join(getattr(loi, "messages", [str(loi)]))) from loi
        self.stdout.write(self.style.SUCCESS(ket_qua))
