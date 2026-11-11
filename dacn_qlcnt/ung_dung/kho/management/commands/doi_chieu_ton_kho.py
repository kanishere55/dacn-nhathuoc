"""Đối chiếu số dư tồn kho với chứng từ (chỉ đọc, không sửa dữ liệu).

    python manage.py doi_chieu_ton_kho [--chi-nhanh MA_CHI_NHANH]

Với mỗi (chi nhánh, lô): ton_kho.so_luong phải bằng nhập + chuyển đến + hoàn kho + nhập lại
hàng khách trả + điều chỉnh kiểm kê − bán − chuyển đi − trả nhà cung cấp − xuất hủy.
Có dòng lệch thì in ra và kết thúc với mã lỗi để dùng được trong kiểm thử tự động.
"""

from django.core.management.base import BaseCommand, CommandError

from ung_dung.danh_muc.models import ChiNhanh

from ...doi_chieu import doi_chieu_ton_kho


class Command(BaseCommand):
    help = "So số dư từng lô tại từng chi nhánh với tổng chứng từ; chỉ đọc."

    def add_arguments(self, parser):
        parser.add_argument(
            "--chi-nhanh", help="Mã chi nhánh cần đối chiếu; bỏ trống: mọi chi nhánh."
        )

    def handle(self, *args, **options):
        cac_chi_nhanh = None
        if options["chi_nhanh"]:
            cac_chi_nhanh = ChiNhanh.objects.filter(ma_chi_nhanh=options["chi_nhanh"])
            if not cac_chi_nhanh.exists():
                raise CommandError(f"Không có chi nhánh mã {options['chi_nhanh']}.")
        lech = doi_chieu_ton_kho(cac_chi_nhanh)
        if not lech:
            self.stdout.write(self.style.SUCCESS("Khớp: số dư mọi lô bằng tổng chứng từ."))
            return
        for ton, theo_chung_tu in lech:
            chi_nhanh = ChiNhanh.objects.get(pk=ton.chi_nhanh_id)
            self.stdout.write(
                f"{chi_nhanh.ma_chi_nhanh} · lô {ton.lo_thuoc.ma_lo_thuoc} "
                f"({ton.lo_thuoc.thuoc.ten_thuoc}): sổ tồn {ton.so_luong}, "
                f"theo chứng từ {theo_chung_tu}, lệch {ton.so_luong - theo_chung_tu}"
            )
        raise CommandError(f"Có {len(lech)} dòng tồn lệch với chứng từ.")
