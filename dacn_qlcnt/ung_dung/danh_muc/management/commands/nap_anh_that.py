"""Nạp ảnh chụp thật (giấy phép mở, Wikimedia Commons) cho thuốc và chi nhánh.

    python manage.py nap_anh_that [--thay-anh-khong-nguon]

Ảnh tải về được kiểm SHA-256, chuẩn hóa WebP rồi lưu bytea trong PostgreSQL cùng tác giả, giấy phép
và đường dẫn nguồn. Dòng nguồn có ghi chú khi ảnh chỉ cùng nhãn hiệu hoặc cùng hoạt chất với sản phẩm.
Chạy lại được và KHÔNG xóa gì: ảnh đã nạp chỉ được cập nhật dòng nguồn, thuốc hoặc chi nhánh đã có ảnh
do quản trị tải lên thì giữ nguyên. Chỉ khi truyền --thay-anh-khong-nguon, ảnh không ghi nguồn của các
thuốc mẫu mới bị xóa để nhường chỗ cho ảnh mở.
"""

import hashlib
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...anh_that import (
    ANH_CHI_NHANH,
    ANH_THUOC,
    GHI_CHU_CHI_NHANH,
    GHI_CHU_KHOP,
    MUC_KHOP,
)
from ...models import AnhChiNhanh, AnhThuoc, ChiNhanh, Thuoc

# Hai hạng mục ghép với nhau: chi nhánh thứ i (theo mã) nhận các ảnh trong NHOM_CHI_NHANH[i].
NHOM_CHI_NHANH = [[0, 1], [2], [3]]


def ghi_nguon(muc, ghi_chu=""):
    return f"{ghi_chu}{muc['tac_gia']} · {muc['giay_phep']} · {muc['trang']}"


class Command(BaseCommand):
    help = "Nạp ảnh thật có giấy phép mở cho thuốc và chi nhánh."

    def add_arguments(self, parser):
        parser.add_argument(
            "--thay-anh-khong-nguon",
            action="store_true",
            help="Xóa ảnh không ghi nguồn của thuốc mẫu trước khi nạp ảnh mở.",
        )

    def _tai(self, muc):
        yeu_cau = urllib.request.Request(
            muc["url"], headers={"User-Agent": settings.HTTP_USER_AGENT}
        )
        for lan in range(3):
            try:
                with urllib.request.urlopen(yeu_cau, timeout=60) as phan_hoi:
                    du_lieu = phan_hoi.read()
                break
            except (urllib.error.URLError, TimeoutError) as loi:
                if lan == 2:
                    raise CommandError(f"Không tải được ảnh {muc['trang']}: {loi}") from loi
                time.sleep(3 * (lan + 1))
        if hashlib.sha256(du_lieu).hexdigest() != muc["sha256"]:
            raise CommandError(f"Ảnh tải về không khớp mã băm, không lưu: {muc['trang']}")
        return du_lieu

    def _them(self, model_anh, chu, ten_khoa, muc, du_lieu, thu_tu, ghi_chu):
        """Thêm ảnh nếu chưa có; ảnh đã nạp (nhận theo trang nguồn) chỉ cập nhật dòng nguồn."""
        nguon = ghi_nguon(muc, ghi_chu)
        da_nap = model_anh.objects.filter(**{ten_khoa: chu}, nguon_anh__contains=muc["trang"])
        if da_nap.exists():
            da_nap.exclude(nguon_anh=nguon).update(nguon_anh=nguon)
            return False
        if model_anh.objects.filter(**{ten_khoa: chu}).exists():
            return False  # đã có ảnh do quản trị tải lên, không chèn thêm ảnh mẫu
        anh = model_anh(**{ten_khoa: chu}, thu_tu=thu_tu, nguon_anh=nguon)
        anh.gan_du_lieu(SimpleUploadedFile("anh.jpg", du_lieu, "image/jpeg"))
        anh.save()
        return True

    def handle(self, *args, **options):
        cac_thuoc = {t.ma_thuoc: t for t in Thuoc.objects.filter(ma_thuoc__startswith="TA-")}
        cac_chi_nhanh = list(ChiNhanh.objects.order_by("ma_chi_nhanh")[: len(NHOM_CHI_NHANH)])
        du_lieu = {}
        for ma, muc in ANH_THUOC.items():
            if ma in cac_thuoc:
                du_lieu[muc["url"]] = self._tai(muc)
                time.sleep(1)
        for so in range(len(cac_chi_nhanh)):
            for vi_tri in NHOM_CHI_NHANH[so]:
                muc = ANH_CHI_NHANH[vi_tri]
                du_lieu[muc["url"]] = self._tai(muc)
                time.sleep(1)
        so_moi = 0
        with transaction.atomic():
            if options["thay_anh_khong_nguon"]:
                da_xoa, _ = AnhThuoc.objects.filter(
                    thuoc__in=cac_thuoc.values(), nguon_anh=""
                ).delete()
                self.stdout.write(f"Xóa {da_xoa} ảnh minh họa không ghi nguồn của thuốc mẫu.")
            for ma, thuoc in cac_thuoc.items():
                muc = ANH_THUOC.get(ma)
                if muc is None:
                    self.stdout.write(
                        self.style.WARNING(f"{ma}: chưa có ảnh mở phù hợp, để trống.")
                    )
                    continue
                ghi_chu = GHI_CHU_KHOP[MUC_KHOP[ma]]
                if self._them(AnhThuoc, thuoc, "thuoc", muc, du_lieu[muc["url"]], 0, ghi_chu):
                    so_moi += 1
            for so, chi_nhanh in enumerate(cac_chi_nhanh):
                for thu_tu, vi_tri in enumerate(NHOM_CHI_NHANH[so]):
                    muc = ANH_CHI_NHANH[vi_tri]
                    if self._them(
                        AnhChiNhanh,
                        chi_nhanh,
                        "chi_nhanh",
                        muc,
                        du_lieu[muc["url"]],
                        thu_tu,
                        GHI_CHU_CHI_NHANH,
                    ):
                        so_moi += 1
        self.stdout.write(self.style.SUCCESS(f"Đã nạp {so_moi} ảnh thật."))
