from django.db import models
from django.db.models.functions import Now

from ung_dung.chung.ten_csdl import rang_buoc_so, rang_buoc_van_ban, ten_rang_buoc


class PhieuTraNhaCungCap(models.Model):
    id_phieu_tra_nha_cung_cap = models.BigAutoField(
        db_column="id_phieu_tra_nha_cung_cap",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_phieu_tra_nha_cung_cap = models.TextField(
        db_column="ma_phieu_tra_nha_cung_cap",
        db_comment="Mã chứng từ hệ thống cấp; văn bản một dòng.",
    )
    phieu_nhap = models.ForeignKey(
        "kho.PhieuNhap",
        on_delete=models.PROTECT,
        db_column="id_phieu_nhap",
        db_comment="Phiếu nhập gốc, xác định nhà cung cấp và chi nhánh.",
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
        db_table = "phieu_tra_nha_cung_cap"
        db_table_comment = "Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa."
        verbose_name = "Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa."
        constraints = [
            *rang_buoc_van_ban(
                "phieu_tra_nha_cung_cap", "ma_phieu_tra_nha_cung_cap", rong=False, nhieu_dong=False
            ),
            *rang_buoc_van_ban("phieu_tra_nha_cung_cap", "ghi_chu", rong=True, nhieu_dong=True),
            models.UniqueConstraint(
                fields=["ma_phieu_tra_nha_cung_cap"],
                name=ten_rang_buoc(
                    "duy_nhat", "phieu_tra_nha_cung_cap", *["ma_phieu_tra_nha_cung_cap"]
                ),
            ),
        ]

    def __str__(self):
        return str(self.ma_phieu_tra_nha_cung_cap)


class ChiTietPhieuTraNhaCungCap(models.Model):
    id_chi_tiet_phieu_tra_nha_cung_cap = models.BigAutoField(
        db_column="id_chi_tiet_phieu_tra_nha_cung_cap",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    phieu_tra_nha_cung_cap = models.ForeignKey(
        "kho.PhieuTraNhaCungCap",
        on_delete=models.PROTECT,
        db_column="id_phieu_tra_nha_cung_cap",
        db_comment="Chứng từ trả sở hữu dòng.",
    )
    lo_thuoc = models.ForeignKey(
        "kho.LoThuoc",
        on_delete=models.PROTECT,
        db_column="id_lo_thuoc",
        db_comment="Lô trả đối tác.",
    )
    so_luong = models.IntegerField(
        db_column="so_luong", db_comment="Lượng cơ sở trả; giới hạn số nguyên PostgreSQL 32 bit."
    )

    class Meta:
        db_table = "chi_tiet_phieu_tra_nha_cung_cap"
        db_table_comment = "Mỗi hàng là lượng trả của một lô đã nhập trong phiếu gốc."
        verbose_name = "Mỗi hàng là lượng trả của một lô đã nhập trong phiếu gốc."
        constraints = [
            *rang_buoc_so("chi_tiet_phieu_tra_nha_cung_cap", "so_luong", duong=True, tien=False),
        ]
