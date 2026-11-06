from django.db import models
from django.db.models.functions import Now

from ung_dung.chung.ten_csdl import rang_buoc_so, rang_buoc_van_ban, ten_rang_buoc


class PhieuKiemKe(models.Model):
    id_phieu_kiem_ke = models.BigAutoField(
        db_column="id_phieu_kiem_ke",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_phieu_kiem_ke = models.TextField(
        db_column="ma_phieu_kiem_ke", db_comment="Mã chứng từ hệ thống cấp; văn bản một dòng."
    )
    chi_nhanh = models.ForeignKey(
        "danh_muc.ChiNhanh",
        on_delete=models.PROTECT,
        db_column="id_chi_nhanh",
        db_comment="Chi nhánh kiểm kê và điều chỉnh ngay khi xác nhận.",
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
        db_table = "phieu_kiem_ke"
        db_table_comment = "Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa."
        verbose_name = "Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa."
        constraints = [
            *rang_buoc_van_ban("phieu_kiem_ke", "ma_phieu_kiem_ke", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("phieu_kiem_ke", "ghi_chu", rong=True, nhieu_dong=True),
            models.UniqueConstraint(
                fields=["ma_phieu_kiem_ke"],
                name=ten_rang_buoc("duy_nhat", "phieu_kiem_ke", *["ma_phieu_kiem_ke"]),
            ),
        ]

    def __str__(self):
        return str(self.ma_phieu_kiem_ke)


class ChiTietPhieuKiemKe(models.Model):
    id_chi_tiet_phieu_kiem_ke = models.BigAutoField(
        db_column="id_chi_tiet_phieu_kiem_ke",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    phieu_kiem_ke = models.ForeignKey(
        "kho.PhieuKiemKe",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_phieu_kiem_ke",
        db_comment="Phiếu kiểm kê.",
    )
    lo_thuoc = models.ForeignKey(
        "kho.LoThuoc", on_delete=models.PROTECT, db_column="id_lo_thuoc", db_comment="Lô được đếm."
    )
    so_luong_so_sach = models.IntegerField(
        db_column="so_luong_so_sach",
        db_comment="Số dư ngay trước khi xác nhận; giới hạn số nguyên PostgreSQL 32 bit.",
    )
    so_luong_thuc_te = models.IntegerField(
        db_column="so_luong_thuc_te",
        db_comment="Lượng cơ sở được đếm; giới hạn số nguyên PostgreSQL 32 bit.",
    )

    class Meta:
        db_table = "chi_tiet_phieu_kiem_ke"
        db_table_comment = "Mỗi hàng là kết quả đếm một lô và số dư được đối chiếu trong giao dịch."
        verbose_name = "Mỗi hàng là kết quả đếm một lô và số dư được đối chiếu trong giao dịch."
        constraints = [
            *rang_buoc_so("chi_tiet_phieu_kiem_ke", "so_luong_so_sach", duong=False, tien=False),
            *rang_buoc_so("chi_tiet_phieu_kiem_ke", "so_luong_thuc_te", duong=False, tien=False),
            models.UniqueConstraint(
                fields=["phieu_kiem_ke", "lo_thuoc"],
                name=ten_rang_buoc(
                    "duy_nhat", "chi_tiet_phieu_kiem_ke", *["id_phieu_kiem_ke", "id_lo_thuoc"]
                ),
            ),
        ]
