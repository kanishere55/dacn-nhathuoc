"""Trường dùng chung cho các chứng từ kho."""

from uuid import uuid4

from django.db import models

from ung_dung.chung.ten_csdl import MA_UUID, rang_buoc_van_ban, ten_rang_buoc


def tao_khoa_yeu_cau():
    """UUID dạng chữ thường, đúng mẫu MA_UUID; dùng khi chứng từ được lập ngoài form."""
    return str(uuid4())


def truong_khoa_yeu_cau():
    return models.TextField(
        db_column="khoa_yeu_cau",
        db_comment=(
            "UUID do form cấp mỗi lần mở; bấm lưu hai lần hoặc gửi lại form chỉ tạo một "
            "chứng từ. Văn bản một dòng."
        ),
        default=tao_khoa_yeu_cau,
    )


def rang_buoc_khoa_yeu_cau(bang):
    """CHECK đúng mẫu UUID và UNIQUE: lớp chặn cuối cho việc gửi trùng một form."""
    return [
        *rang_buoc_van_ban(bang, "khoa_yeu_cau", dinh_dang=MA_UUID),
        models.UniqueConstraint(
            fields=["khoa_yeu_cau"], name=ten_rang_buoc("duy_nhat", bang, "khoa_yeu_cau")
        ),
    ]
