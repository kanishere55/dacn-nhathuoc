"""Ảnh lưu thẳng trong PostgreSQL (bytea).

Ảnh tải lên được mở bằng Pillow, xoay theo EXIF, bỏ toàn bộ metadata (vị trí GPS,
thiết bị), thu về cạnh dài tối đa 1600 px và mã hóa lại WebP. Nhờ đó CSDL chỉ giữ
một định dạng, tệp giả mạo đuôi ảnh bị từ chối và kích thước dữ liệu có trần rõ ràng.
"""

import hashlib
from io import BytesIO

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now
from django.http import HttpResponse, HttpResponseNotModified
from PIL import Image, ImageOps, UnidentifiedImageError

from .ten_csdl import ten_rang_buoc

CANH_TOI_DA = 1600
BYTE_TOI_DA = 3 * 1024 * 1024
DINH_DANG_NHAN = {"JPEG", "PNG", "WEBP", "GIF", "MPO"}
Image.MAX_IMAGE_PIXELS = 40_000_000


class DoDaiByte(models.Func):
    function = "octet_length"
    arity = 1
    output_field = models.IntegerField()


def xu_ly_anh(tep):
    """Trả (bytes WebP, rộng, cao, sha256) hoặc ValidationError nếu không phải ảnh."""
    try:
        with Image.open(tep) as anh:
            if anh.format not in DINH_DANG_NHAN:
                raise ValidationError("Chỉ nhận ảnh JPEG, PNG, WebP hoặc GIF.")
            anh = ImageOps.exif_transpose(anh)
            anh = anh.convert("RGBA" if anh.mode in ("RGBA", "LA", "P") else "RGB")
            anh.thumbnail((CANH_TOI_DA, CANH_TOI_DA))
            dau_ra = BytesIO()
            anh.save(dau_ra, "WEBP", quality=82, method=4)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as loi:
        raise ValidationError("Tệp không phải ảnh hợp lệ.") from loi
    du_lieu = dau_ra.getvalue()
    if len(du_lieu) > BYTE_TOI_DA:
        raise ValidationError("Ảnh sau khi nén vẫn quá lớn.")
    return du_lieu, anh.width, anh.height, hashlib.sha256(du_lieu).hexdigest()


class AnhCSDL(models.Model):
    """Các cột chung của bảng ảnh; bảng con thêm khóa ngoại tới đối tượng sở hữu."""

    noi_dung_anh = models.BinaryField(
        db_column="noi_dung_anh",
        db_comment="Dữ liệu ảnh WebP đã chuẩn hóa, không còn metadata của tệp gốc.",
    )
    kich_thuoc_byte = models.IntegerField(
        db_column="kich_thuoc_byte",
        db_comment="Số byte của noi_dung_anh, tối đa 3 MiB.",
    )
    chieu_rong = models.SmallIntegerField(
        db_column="chieu_rong", db_comment="Chiều rộng ảnh theo điểm ảnh, 1 đến 1600."
    )
    chieu_cao = models.SmallIntegerField(
        db_column="chieu_cao", db_comment="Chiều cao ảnh theo điểm ảnh, 1 đến 1600."
    )
    bam_sha256 = models.TextField(
        db_column="bam_sha256",
        db_comment="SHA-256 hệ thập lục phân của noi_dung_anh; dùng làm ETag khi phục vụ.",
    )
    thu_tu = models.SmallIntegerField(
        db_default=0,
        db_column="thu_tu",
        db_comment="Thứ tự hiển thị trong bộ ảnh, số nhỏ đứng trước; ảnh đầu là ảnh đại diện.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_default=Now(), db_column="thoi_diem_tao", db_comment="Thời điểm tải ảnh lên."
    )

    class Meta:
        abstract = True

    def gan_du_lieu(self, tep):
        (
            self.noi_dung_anh,
            self.chieu_rong,
            self.chieu_cao,
            self.bam_sha256,
        ) = xu_ly_anh(tep)
        self.kich_thuoc_byte = len(self.noi_dung_anh)


class AnhCoNguon(AnhCSDL):
    """Ảnh có ghi nguồn và giấy phép, cho ảnh sản phẩm lấy từ kho ảnh mở."""

    nguon_anh = models.TextField(
        blank=True,
        db_default="",
        db_column="nguon_anh",
        db_comment=(
            "Nguồn, tác giả và giấy phép của ảnh (ví dụ ảnh Wikimedia Commons); "
            "một dòng, rỗng với ảnh tự chụp hoặc tự tải lên."
        ),
    )

    class Meta:
        abstract = True


def rang_buoc_anh(bang, *, co_nguon=False):
    from .ten_csdl import rang_buoc_van_ban

    return [
        *(rang_buoc_van_ban(bang, "nguon_anh", rong=True) if co_nguon else []),
        *rang_buoc_van_ban(bang, "bam_sha256", dinh_dang=r"^[0-9a-f]{64}$"),
        models.CheckConstraint(
            condition=Q(kich_thuoc_byte=DoDaiByte("noi_dung_anh"))
            & Q(kich_thuoc_byte__gte=1, kich_thuoc_byte__lte=BYTE_TOI_DA),
            name=ten_rang_buoc("kiem_tra", bang, "kich_thuoc_byte_khop"),
        ),
        models.CheckConstraint(
            condition=Q(chieu_rong__gte=1, chieu_rong__lte=CANH_TOI_DA)
            & Q(chieu_cao__gte=1, chieu_cao__lte=CANH_TOI_DA),
            name=ten_rang_buoc("kiem_tra", bang, "kich_thuoc_anh_hop_le"),
        ),
        models.CheckConstraint(
            condition=Q(thu_tu__gte=0), name=ten_rang_buoc("kiem_tra", bang, "thu_tu_khong_am")
        ),
    ]


def tra_anh(request, anh, *, cong_khai=True):
    """Trả ảnh kèm ETag. Ảnh công khai được cache vì nội dung theo id không đổi;
    ảnh riêng tư (minh chứng của khách) không được lưu ở cache dùng chung."""
    etag = f'"{anh.bam_sha256}"'
    if cong_khai and request.headers.get("If-None-Match") == etag:
        return HttpResponseNotModified()
    phan_hoi = HttpResponse(bytes(anh.noi_dung_anh), content_type="image/webp")
    phan_hoi["ETag"] = etag
    phan_hoi["Cache-Control"] = (
        "public, max-age=604800, immutable" if cong_khai else "private, no-store"
    )
    phan_hoi["X-Content-Type-Options"] = "nosniff"
    return phan_hoi
