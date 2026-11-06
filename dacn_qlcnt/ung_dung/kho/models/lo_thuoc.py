from django.db import models

from ung_dung.chung.ten_csdl import rang_buoc_van_ban, ten_rang_buoc


class LoThuoc(models.Model):
    id_lo_thuoc = models.BigAutoField(
        db_column="id_lo_thuoc",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    thuoc = models.ForeignKey(
        "danh_muc.Thuoc",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_thuoc",
        db_comment="Sản phẩm của lô.",
    )
    ma_lo_thuoc = models.TextField(
        db_column="ma_lo_thuoc", db_comment="Mã lô của nhà sản xuất; văn bản một dòng."
    )
    ngay_het_han = models.DateField(
        db_column="ngay_het_han",
        db_comment="Ngày cuối lô còn được bán theo giờ Việt Nam, do người nhập ghi.",
    )
    duoc_phep_ban = models.BooleanField(
        db_column="duoc_phep_ban", db_comment="Lô được phép xuất bán khi còn hạn.", db_default=True
    )

    class Meta:
        db_table = "lo_thuoc"
        db_table_comment = "Mỗi hàng là một lô của một thuốc, dùng chung giữa các chi nhánh."
        verbose_name = "Mỗi hàng là một lô của một thuốc, dùng chung giữa các chi nhánh."
        constraints = [
            *rang_buoc_van_ban("lo_thuoc", "ma_lo_thuoc", rong=False, nhieu_dong=False),
            models.UniqueConstraint(
                fields=["thuoc", "ma_lo_thuoc"],
                name=ten_rang_buoc("duy_nhat", "lo_thuoc", *["id_thuoc", "ma_lo_thuoc"]),
            ),
        ]

    def __str__(self):
        return str(self.ma_lo_thuoc)
