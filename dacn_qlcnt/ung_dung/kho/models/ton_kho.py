from django.db import models

from ung_dung.chung.ten_csdl import rang_buoc_so, ten_rang_buoc


class TonKho(models.Model):
    id_ton_kho = models.BigAutoField(
        db_column="id_ton_kho",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    chi_nhanh = models.ForeignKey(
        "danh_muc.ChiNhanh",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_chi_nhanh",
        db_comment="Chi nhánh giữ hàng.",
    )
    lo_thuoc = models.ForeignKey(
        "kho.LoThuoc", on_delete=models.PROTECT, db_column="id_lo_thuoc", db_comment="Lô hàng tồn."
    )
    so_luong = models.IntegerField(
        db_column="so_luong",
        db_comment="Số lượng vật lý theo đơn vị cơ sở; giới hạn số nguyên PostgreSQL 32 bit.",
        db_default=0,
    )

    class Meta:
        db_table = "ton_kho"
        db_table_comment = "Mỗi hàng là số dư vật lý của một lô tại một chi nhánh."
        verbose_name = "Mỗi hàng là số dư vật lý của một lô tại một chi nhánh."
        constraints = [
            *rang_buoc_so("ton_kho", "so_luong", duong=False, tien=False),
            models.UniqueConstraint(
                fields=["chi_nhanh", "lo_thuoc"],
                name=ten_rang_buoc("duy_nhat", "ton_kho", *["id_chi_nhanh", "id_lo_thuoc"]),
            ),
        ]
