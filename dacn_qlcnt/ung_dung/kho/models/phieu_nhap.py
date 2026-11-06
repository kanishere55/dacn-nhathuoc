from django.db import models
from django.db.models.functions import Now

from ung_dung.chung.ten_csdl import rang_buoc_so, rang_buoc_van_ban, ten_rang_buoc


class PhieuNhap(models.Model):
    id_phieu_nhap = models.BigAutoField(
        db_column="id_phieu_nhap",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_phieu_nhap = models.TextField(
        db_column="ma_phieu_nhap", db_comment="Mã chứng từ hệ thống cấp; văn bản một dòng."
    )
    chi_nhanh = models.ForeignKey(
        "danh_muc.ChiNhanh",
        on_delete=models.PROTECT,
        db_column="id_chi_nhanh",
        db_comment="Chi nhánh nhận hàng.",
    )
    nha_cung_cap = models.ForeignKey(
        "danh_muc.NhaCungCap",
        on_delete=models.PROTECT,
        db_column="id_nha_cung_cap",
        db_comment="Đối tác giao hàng.",
    )
    nguoi_lap = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        on_delete=models.PROTECT,
        db_column="id_tai_khoan_lap",
        db_comment="Tài khoản xác nhận chứng từ.",
    )
    ghi_chu = models.TextField(
        db_column="ghi_chu",
        db_comment="Ghi chú khi xác nhận; cho phép nhiều dòng.",
        blank=True,
        db_default="",
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "phieu_nhap"
        db_table_comment = "Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa."
        verbose_name = "Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa."
        constraints = [
            *rang_buoc_van_ban("phieu_nhap", "ma_phieu_nhap", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("phieu_nhap", "ghi_chu", rong=True, nhieu_dong=True),
            models.UniqueConstraint(
                fields=["ma_phieu_nhap"],
                name=ten_rang_buoc("duy_nhat", "phieu_nhap", *["ma_phieu_nhap"]),
            ),
        ]

    def __str__(self):
        return str(self.ma_phieu_nhap)


class ChiTietPhieuNhap(models.Model):
    id_chi_tiet_phieu_nhap = models.BigAutoField(
        db_column="id_chi_tiet_phieu_nhap",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    phieu_nhap = models.ForeignKey(
        "kho.PhieuNhap",
        on_delete=models.PROTECT,
        db_column="id_phieu_nhap",
        db_comment="Phiếu nhập sở hữu dòng.",
    )
    lo_thuoc = models.ForeignKey(
        "kho.LoThuoc", on_delete=models.PROTECT, db_column="id_lo_thuoc", db_comment="Lô thực nhập."
    )
    so_luong = models.IntegerField(
        db_column="so_luong", db_comment="Lượng cơ sở nhập; giới hạn số nguyên PostgreSQL 32 bit."
    )
    don_gia = models.DecimalField(
        db_column="don_gia",
        db_comment="Giá nhập một đơn vị cơ sở; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.",
        max_digits=14,
        decimal_places=0,
    )

    class Meta:
        db_table = "chi_tiet_phieu_nhap"
        db_table_comment = "Mỗi hàng là lượng nhập của một lô trong phiếu nhập."
        verbose_name = "Mỗi hàng là lượng nhập của một lô trong phiếu nhập."
        constraints = [
            *rang_buoc_so("chi_tiet_phieu_nhap", "so_luong", duong=True, tien=False),
            *rang_buoc_so("chi_tiet_phieu_nhap", "don_gia", duong=False, tien=True),
        ]
