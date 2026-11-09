from django.db import models
from django.db.models.functions import Now

from ung_dung.chung.ten_csdl import rang_buoc_so, rang_buoc_van_ban, ten_rang_buoc

LOAI_XUAT_HUY = (("het_han", "Hết hạn dùng"), ("hu_hong", "Hư hỏng, biến chất"))


class PhieuXuatHuy(models.Model):
    id_phieu_xuat_huy = models.BigAutoField(
        db_column="id_phieu_xuat_huy",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_phieu_xuat_huy = models.TextField(
        db_column="ma_phieu_xuat_huy", db_comment="Mã chứng từ hệ thống cấp; văn bản một dòng."
    )
    chi_nhanh = models.ForeignKey(
        "danh_muc.ChiNhanh",
        on_delete=models.PROTECT,
        db_column="id_chi_nhanh",
        db_comment="Chi nhánh có hàng bị hủy.",
    )
    nguoi_lap = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        on_delete=models.PROTECT,
        db_column="id_tai_khoan_lap",
        db_comment="Quản lý chi nhánh xác nhận chứng từ.",
    )
    loai_xuat_huy = models.TextField(
        choices=LOAI_XUAT_HUY,
        db_column="loai_xuat_huy",
        db_comment="het_han: mọi lô đã quá ngày hết hạn; hu_hong: hàng hỏng, vỡ, biến chất.",
    )
    ghi_chu = models.TextField(
        db_column="ghi_chu",
        db_comment="Mô tả tình trạng hàng và biên bản kèm theo; cho phép nhiều dòng.",
        blank=True,
        db_default="",
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "phieu_xuat_huy"
        db_table_comment = "Mỗi hàng là một chứng từ xuất hủy đã xác nhận, không sửa hoặc xóa."
        verbose_name = "phiếu xuất hủy"
        constraints = [
            *rang_buoc_van_ban("phieu_xuat_huy", "ma_phieu_xuat_huy"),
            *rang_buoc_van_ban("phieu_xuat_huy", "ghi_chu", rong=True, nhieu_dong=True),
            models.CheckConstraint(
                condition=models.Q(loai_xuat_huy__in=[ma for ma, _ in LOAI_XUAT_HUY]),
                name=ten_rang_buoc("kiem_tra", "phieu_xuat_huy", "loai_xuat_huy_hop_le"),
            ),
            models.UniqueConstraint(
                fields=["ma_phieu_xuat_huy"],
                name=ten_rang_buoc("duy_nhat", "phieu_xuat_huy", "ma_phieu_xuat_huy"),
            ),
        ]

    def __str__(self):
        return str(self.ma_phieu_xuat_huy)


class ChiTietPhieuXuatHuy(models.Model):
    id_chi_tiet_phieu_xuat_huy = models.BigAutoField(
        db_column="id_chi_tiet_phieu_xuat_huy",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    phieu_xuat_huy = models.ForeignKey(
        "kho.PhieuXuatHuy",
        on_delete=models.PROTECT,
        db_column="id_phieu_xuat_huy",
        db_comment="Chứng từ xuất hủy sở hữu dòng.",
    )
    lo_thuoc = models.ForeignKey(
        "kho.LoThuoc",
        on_delete=models.PROTECT,
        db_column="id_lo_thuoc",
        db_comment="Lô bị hủy tại chi nhánh của phiếu.",
    )
    so_luong = models.IntegerField(
        db_column="so_luong", db_comment="Lượng cơ sở hủy; giới hạn số nguyên PostgreSQL 32 bit."
    )

    class Meta:
        db_table = "chi_tiet_phieu_xuat_huy"
        db_table_comment = "Mỗi hàng là lượng một lô bị hủy trong phiếu xuất hủy."
        verbose_name = "chi tiết phiếu xuất hủy"
        constraints = [
            *rang_buoc_so("chi_tiet_phieu_xuat_huy", "so_luong", duong=True),
        ]
