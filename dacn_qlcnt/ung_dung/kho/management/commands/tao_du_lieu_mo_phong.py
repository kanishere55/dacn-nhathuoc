from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError

from ...services.mo_phong import bo_sung_noi_dung_mo_phong, tao_du_lieu_mo_phong


class Command(BaseCommand):
    help = "Sinh dữ liệu nhà thuốc mô phỏng trực tiếp vào PostgreSQL."

    def add_arguments(self, parser):
        parser.add_argument(
            "--quan-tri", required=True, help="Tên tài khoản quản trị đang hoạt động."
        )
        parser.add_argument(
            "--kem-tai-khoan",
            action="store_true",
            help="Tạo thêm khách và đặt mật khẩu đăng nhập cho các tài khoản mô phỏng.",
        )
        parser.add_argument(
            "--bo-sung",
            action="store_true",
            help="Chỉ bổ sung danh mục, nội dung hiển thị và khuyến mãi cho dữ liệu mô phỏng đã có.",
        )

    def handle(self, *args, **options):
        quan_tri = get_user_model().objects.filter(ten_dang_nhap=options["quan_tri"]).first()
        if quan_tri is None:
            raise CommandError("Không tìm thấy quản trị. Tạo bằng createsuperuser trước.")
        if options["bo_sung"]:
            bo_sung_noi_dung_mo_phong(quan_tri)
            self.stdout.write(self.style.SUCCESS("Đã bổ sung nội dung cho dữ liệu mô phỏng."))
            return
        mat_khau = getpass("Mật khẩu tài khoản mô phỏng: ") if options["kem_tai_khoan"] else None
        try:
            ket_qua = tao_du_lieu_mo_phong(quan_tri, mat_khau=mat_khau)
        except (ValueError, PermissionDenied, ValidationError) as loi:
            raise CommandError(str(loi)) from loi
        self.stdout.write(self.style.SUCCESS(ket_qua))
