"""Nạp ảnh chụp thật (giấy phép mở, Wikimedia Commons) cho thuốc và chi nhánh.

    python manage.py nap_anh_that [--thay-anh-khong-nguon]

Mỗi thuốc và chi nhánh mẫu có một bộ vài ảnh (xem anh_that.py) để trang chi tiết và popup bản đồ có ảnh
trượt. Ảnh tải về được kiểm SHA-256, chuẩn hóa WebP rồi lưu bytea trong PostgreSQL cùng tác giả, giấy
phép và đường dẫn nguồn. Dòng nguồn có ghi chú khi ảnh chỉ cùng nhãn hiệu hoặc cùng hoạt chất.
Chạy lại được và KHÔNG xóa gì: chỉ tải ảnh còn thiếu, ảnh đã nạp chỉ được cập nhật dòng nguồn; thuốc
hoặc chi nhánh đã có ảnh do quản trị tải lên thì giữ nguyên, không chèn ảnh mẫu. Chỉ khi truyền
--thay-anh-khong-nguon, ảnh không ghi nguồn của các thuốc mẫu mới bị xóa để nhường chỗ cho ảnh mở.
"""

import hashlib
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction

from ...anh_that import (
    ANH_CHI_NHANH,
    ANH_THUOC,
    ANH_THUOC_THEM,
    GHI_CHU_CHI_NHANH,
    GHI_CHU_KHOP,
    MUC_KHOP,
    NHOM_CHI_NHANH,
)
from ...models import AnhChiNhanh, AnhThuoc, ChiNhanh, Thuoc

# Trang nguồn của mọi ảnh mẫu: ảnh có dòng nguồn chứa một trong các trang này là ảnh do lệnh nạp.
TRANG_MAU = tuple(
    {m["trang"] for m in ANH_THUOC.values()}
    | {m["trang"] for ds in ANH_THUOC_THEM.values() for m in ds}
    | {m["trang"] for m in ANH_CHI_NHANH}
)


def ghi_nguon(muc, ghi_chu=""):
    return f"{ghi_chu}{muc['tac_gia']} · {muc['giay_phep']} · {muc['trang']}"


def cac_anh_thuoc(ma):
    """Bộ ảnh mẫu của một thuốc theo thứ tự hiển thị: [(mục ảnh, ghi chú mức khớp), ...]."""
    bo_anh = [(ANH_THUOC[ma], GHI_CHU_KHOP[MUC_KHOP[ma]])] if ma in ANH_THUOC else []
    return bo_anh + [(m, GHI_CHU_KHOP[m["khop"]]) for m in ANH_THUOC_THEM.get(ma, [])]


class Command(BaseCommand):
    help = "Nạp ảnh thật có giấy phép mở cho thuốc và chi nhánh."

    def add_arguments(self, parser):
        parser.add_argument(
            "--thay-anh-khong-nguon",
            action="store_true",
            help="Xóa ảnh không ghi nguồn của thuốc mẫu trước khi nạp ảnh mở.",
        )

    def _tai(self, muc):
        """Tải một ảnh và kiểm mã băm. Lỗi mạng hoặc sai mã băm thì bỏ qua ảnh đó (báo cảnh báo),
        các ảnh khác vẫn được nạp; chạy lại lệnh sau để bù ảnh còn thiếu."""
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
                    self.stdout.write(
                        self.style.WARNING(f"Không tải được ảnh {muc['trang']}: {loi}. Bỏ qua.")
                    )
                    return None
                time.sleep(3 * (lan + 1))
        if hashlib.sha256(du_lieu).hexdigest() != muc["sha256"]:
            self.stdout.write(
                self.style.WARNING(f"Ảnh tải về không khớp mã băm, không lưu: {muc['trang']}")
            )
            return None
        return du_lieu

    @staticmethod
    def _co_anh_quan_tri(model_anh, ten_khoa, chu):
        """Đã có ảnh không phải ảnh mẫu (quản trị tự tải lên) thì không chèn ảnh mẫu."""
        cac_nguon = model_anh.objects.filter(**{ten_khoa: chu}).values_list("nguon_anh", flat=True)
        return any(not any(trang in nguon for trang in TRANG_MAU) for nguon in cac_nguon)

    def _them(self, model_anh, chu, ten_khoa, muc, du_lieu, thu_tu, ghi_chu):
        """Thêm ảnh nếu chưa có; ảnh đã nạp (nhận theo trang nguồn) chỉ cập nhật dòng nguồn."""
        nguon = ghi_nguon(muc, ghi_chu)
        da_nap = model_anh.objects.filter(**{ten_khoa: chu}, nguon_anh__contains=muc["trang"])
        if da_nap.exists():
            da_nap.exclude(nguon_anh=nguon).update(nguon_anh=nguon)
            return False
        if du_lieu is None or self._co_anh_quan_tri(model_anh, ten_khoa, chu):
            return False
        anh = model_anh(**{ten_khoa: chu}, thu_tu=thu_tu, nguon_anh=nguon)
        anh.gan_du_lieu(SimpleUploadedFile("anh.jpg", du_lieu, "image/jpeg"))
        anh.save()
        return True

    def _can_tai(self, model_anh, ten_khoa, chu, muc):
        da_nap = model_anh.objects.filter(**{ten_khoa: chu}, nguon_anh__contains=muc["trang"])
        return not da_nap.exists() and not self._co_anh_quan_tri(model_anh, ten_khoa, chu)

    def handle(self, *args, **options):
        cac_thuoc = {t.ma_thuoc: t for t in Thuoc.objects.filter(ma_thuoc__startswith="TA-")}
        cac_chi_nhanh = list(ChiNhanh.objects.order_by("ma_chi_nhanh")[: len(NHOM_CHI_NHANH)])
        # Mỗi việc: (model ảnh, chủ ảnh, tên khóa, mục ảnh, thứ tự, ghi chú đầu dòng nguồn).
        cac_viec = []
        for ma, thuoc in cac_thuoc.items():
            bo_anh = cac_anh_thuoc(ma)
            if not bo_anh:
                self.stdout.write(self.style.WARNING(f"{ma}: chưa có ảnh mở phù hợp, để trống."))
            for thu_tu, (muc, ghi_chu) in enumerate(bo_anh):
                cac_viec.append((AnhThuoc, thuoc, "thuoc", muc, thu_tu, ghi_chu))
        for so, chi_nhanh in enumerate(cac_chi_nhanh):
            for thu_tu, vi_tri in enumerate(NHOM_CHI_NHANH[so]):
                muc = ANH_CHI_NHANH[vi_tri]
                cac_viec.append(
                    (AnhChiNhanh, chi_nhanh, "chi_nhanh", muc, thu_tu, GHI_CHU_CHI_NHANH)
                )
        if options["thay_anh_khong_nguon"]:
            with transaction.atomic():
                da_xoa, _ = AnhThuoc.objects.filter(
                    thuoc__in=cac_thuoc.values(), nguon_anh=""
                ).delete()
            self.stdout.write(f"Xóa {da_xoa} ảnh minh họa không ghi nguồn của thuốc mẫu.")
        # Chỉ tải ảnh còn thiếu, nghỉ giữa các lượt tải để không bị máy chủ ảnh giới hạn.
        du_lieu = {}
        for model_anh, chu, ten_khoa, muc, _, _ in cac_viec:
            if muc["url"] not in du_lieu and self._can_tai(model_anh, ten_khoa, chu, muc):
                du_lieu[muc["url"]] = self._tai(muc)
                time.sleep(1)
        if not all(du_lieu.values()):
            self.stdout.write(self.style.WARNING("Có ảnh chưa tải được; chạy lại lệnh để nạp bù."))
        so_moi = 0
        with transaction.atomic():
            for model_anh, chu, ten_khoa, muc, thu_tu, ghi_chu in cac_viec:
                if self._them(
                    model_anh, chu, ten_khoa, muc, du_lieu.get(muc["url"]), thu_tu, ghi_chu
                ):
                    so_moi += 1
        self.stdout.write(self.style.SUCCESS(f"Đã nạp {so_moi} ảnh thật."))
