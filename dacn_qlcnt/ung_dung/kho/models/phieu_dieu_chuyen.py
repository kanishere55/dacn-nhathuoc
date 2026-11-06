from django.db import models
from django.db.models.functions import Now

from ung_dung.chung.ten_csdl import rang_buoc_so, rang_buoc_van_ban, ten_rang_buoc


class PhieuDieuChuyen(models.Model):
    id_phieu_dieu_chuyen = models.BigAutoField(
        db_column="id_phieu_dieu_chuyen",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_phieu_dieu_chuyen = models.TextField(
        db_column="ma_phieu_dieu_chuyen", db_comment="Mã chứng từ hệ thống cấp; văn bản một dòng."
    )
    chi_nhanh_nguon = models.ForeignKey(
        "danh_muc.ChiNhanh",
        on_delete=models.PROTECT,
        db_column="id_chi_nhanh_nguon",
        db_comment="Cơ sở xuất hàng.",
        related_name="cac_phieu_chuyen_di",
    )
    chi_nhanh_dich = models.ForeignKey(
        "danh_muc.ChiNhanh",
        on_delete=models.PROTECT,
        db_column="id_chi_nhanh_dich",
        db_comment="Cơ sở nhận hàng đồng thời trong giao dịch.",
        related_name="cac_phieu_nhan_den",
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
        db_table = "phieu_dieu_chuyen"
        db_table_comment = "Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa."
        verbose_name = "Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa."
        constraints = [
            *rang_buoc_van_ban(
                "phieu_dieu_chuyen", "ma_phieu_dieu_chuyen", rong=False, nhieu_dong=False
            ),
            *rang_buoc_van_ban("phieu_dieu_chuyen", "ghi_chu", rong=True, nhieu_dong=True),
            models.UniqueConstraint(
                fields=["ma_phieu_dieu_chuyen"],
                name=ten_rang_buoc("duy_nhat", "phieu_dieu_chuyen", *["ma_phieu_dieu_chuyen"]),
            ),
            models.CheckConstraint(
                condition=~models.Q(chi_nhanh_dich=models.F("chi_nhanh_nguon")),
                name="kiem_tra__phieu_dieu_chuyen__nguon_khac_dich",
            ),
        ]

    def __str__(self):
        return str(self.ma_phieu_dieu_chuyen)


class ChiTietPhieuDieuChuyen(models.Model):
    id_chi_tiet_phieu_dieu_chuyen = models.BigAutoField(
        db_column="id_chi_tiet_phieu_dieu_chuyen",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    phieu_dieu_chuyen = models.ForeignKey(
        "kho.PhieuDieuChuyen",
        on_delete=models.PROTECT,
        db_column="id_phieu_dieu_chuyen",
        db_comment="Chứng từ điều chuyển.",
    )
    lo_thuoc = models.ForeignKey(
        "kho.LoThuoc",
        on_delete=models.PROTECT,
        db_column="id_lo_thuoc",
        db_comment="Lô được chuyển.",
    )
    so_luong = models.IntegerField(
        db_column="so_luong", db_comment="Lượng cơ sở chuyển; giới hạn số nguyên PostgreSQL 32 bit."
    )

    class Meta:
        db_table = "chi_tiet_phieu_dieu_chuyen"
        db_table_comment = "Mỗi hàng là lượng một lô đã chuyển giữa hai chi nhánh."
        verbose_name = "Mỗi hàng là lượng một lô đã chuyển giữa hai chi nhánh."
        constraints = [
            *rang_buoc_so("chi_tiet_phieu_dieu_chuyen", "so_luong", duong=True, tien=False),
        ]
