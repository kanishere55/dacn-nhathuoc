"""Nạp các bài tin tức mẫu (chạy lại được, không ghi đè bài đã sửa trong khu quản lý)."""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.noi_dung_phong_phu import lam_sach_html

from ...models import TinTuc
from ...tin_tuc_mau import BAI_VIET


class Command(BaseCommand):
    help = "Đăng các bài tin tức mẫu; bài đã có cùng đường dẫn thì giữ nguyên."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tac-gia",
            default="",
            help="Tên đăng nhập người viết (mặc định: quản trị chuỗi đầu tiên).",
        )

    def handle(self, *args, **options):
        nguoi_dung = get_user_model()
        if options["tac_gia"]:
            tac_gia = nguoi_dung.objects.filter(ten_dang_nhap=options["tac_gia"]).first()
        else:
            tac_gia = (
                nguoi_dung.objects.filter(vai_tro="quan_tri_chuoi", dang_hoat_dong=True)
                .order_by("pk")
                .first()
            )
        if tac_gia is None:
            raise CommandError("Không tìm thấy tài khoản quản trị để ghi là người viết.")
        with transaction.atomic():
            for bai in BAI_VIET:
                thoi_diem = timezone.make_aware(
                    datetime.strptime(bai["thoi_diem_dang"], "%Y-%m-%d %H:%M")
                )
                _, tao = TinTuc.objects.get_or_create(
                    duong_dan_tin_tuc=bai["duong_dan"],
                    defaults={
                        "tieu_de": bai["tieu_de"],
                        "tom_tat": bai["tom_tat"],
                        "noi_dung_tin_tuc": lam_sach_html(bai["noi_dung"]),
                        "nguoi_viet": tac_gia,
                        "dang_hien_thi": True,
                        "thoi_diem_dang": min(thoi_diem, timezone.now()),
                    },
                )
                self.stdout.write(f"{'Đăng' if tao else 'Giữ'} bài {bai['duong_dan']}")
