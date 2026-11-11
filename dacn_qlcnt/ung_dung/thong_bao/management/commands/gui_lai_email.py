"""Gửi lại thư lỗi hoặc kẹt "Chờ gửi" (tiến trình gửi bị dừng), từ bản đã lưu trong CSDL.

    python manage.py gui_lai_email
    python manage.py gui_lai_email --toi-da 20

Bỏ qua thư mã xác thực (không lưu mã), thư cũ chưa lưu bản HTML và thư đã thử 5 lần.
Chạy cùng tác vụ định kỳ với xu_ly_don_qua_han, hoặc chạy tay sau khi sửa cấu hình thư.
"""

from django.core.management.base import BaseCommand

from ung_dung.thong_bao.services import gui_lai_thu_ton


class Command(BaseCommand):
    help = "Gửi lại các thư gửi lỗi hoặc kẹt ở trạng thái chờ gửi."

    def add_arguments(self, parser):
        parser.add_argument("--toi-da", type=int, default=50, help="Số thư tối đa mỗi lần chạy.")

    def handle(self, *args, **tuy_chon):
        da_gui, con_loi = gui_lai_thu_ton(max(1, tuy_chon["toi_da"]))
        self.stdout.write(f"Đã gửi lại {da_gui} thư; {con_loi} thư vẫn lỗi.")
