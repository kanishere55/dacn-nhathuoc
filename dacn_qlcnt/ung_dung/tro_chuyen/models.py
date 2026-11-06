from django.db import models
from django.db.models.functions import Length, Now
from django.db.models.lookups import LessThanOrEqual

from ung_dung.chung.ten_csdl import MA_UUID, rang_buoc_van_ban, ten_rang_buoc


class CuocTroChuyen(models.Model):
    id_cuoc_tro_chuyen = models.BigAutoField(
        db_column="id_cuoc_tro_chuyen",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    khach_hang = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_tai_khoan_khach",
        db_comment="Khách sở hữu phòng.",
    )
    chi_nhanh = models.ForeignKey(
        "danh_muc.ChiNhanh",
        on_delete=models.PROTECT,
        db_column="id_chi_nhanh",
        db_comment="Chi nhánh phụ trách trao đổi.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "cuoc_tro_chuyen"
        db_table_comment = "Mỗi hàng là phòng riêng của một khách với một chi nhánh."
        verbose_name = "Mỗi hàng là phòng riêng của một khách với một chi nhánh."
        constraints = [
            models.UniqueConstraint(
                fields=["khach_hang", "chi_nhanh"],
                name=ten_rang_buoc(
                    "duy_nhat", "cuoc_tro_chuyen", *["id_tai_khoan_khach", "id_chi_nhanh"]
                ),
            ),
        ]


class TinNhan(models.Model):
    id_tin_nhan = models.BigAutoField(
        db_column="id_tin_nhan",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    cuoc_tro_chuyen = models.ForeignKey(
        "tro_chuyen.CuocTroChuyen",
        on_delete=models.PROTECT,
        db_column="id_cuoc_tro_chuyen",
        db_comment="Phòng sở hữu tin.",
    )
    nguoi_gui = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_tai_khoan_gui",
        db_comment="Người gửi được xác định từ phiên đăng nhập.",
    )
    ma_tin_nhan = models.TextField(
        db_column="ma_tin_nhan",
        db_comment="UUID chống gửi trùng do trình duyệt tạo; văn bản một dòng.",
    )
    noi_dung_tin_nhan = models.TextField(
        db_column="noi_dung_tin_nhan",
        db_comment="Nội dung khách/nhân viên nhập; cho phép nhiều dòng.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "tin_nhan"
        db_table_comment = "Mỗi hàng là tin đã được ghi bền vững trước khi phát Redis."
        verbose_name = "Mỗi hàng là tin đã được ghi bền vững trước khi phát Redis."
        constraints = [
            *rang_buoc_van_ban("tin_nhan", "ma_tin_nhan", dinh_dang=MA_UUID),
            *rang_buoc_van_ban("tin_nhan", "noi_dung_tin_nhan", rong=False, nhieu_dong=True),
            models.UniqueConstraint(
                fields=["nguoi_gui", "ma_tin_nhan"],
                name=ten_rang_buoc("duy_nhat", "tin_nhan", *["id_tai_khoan_gui", "ma_tin_nhan"]),
            ),
            models.CheckConstraint(
                condition=LessThanOrEqual(Length("noi_dung_tin_nhan"), 2000),
                name="kiem_tra__tin_nhan__noi_dung_toi_da_2000_ky_tu",
            ),
        ]
