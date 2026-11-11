from django.db import models
from django.db.models.functions import Now

from ung_dung.chung.ten_csdl import rang_buoc_van_ban, ten_rang_buoc
from ung_dung.chung.van_ban import KhongRong


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


class LichSuDieuKienLo(models.Model):
    """Nhật ký khóa và mở bán một lô: ai làm, lúc nào, vì sao, theo văn bản thu hồi nào."""

    id_lich_su_dieu_kien_lo = models.BigAutoField(
        db_column="id_lich_su_dieu_kien_lo",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    lo_thuoc = models.ForeignKey(
        "kho.LoThuoc",
        on_delete=models.PROTECT,
        related_name="cac_lich_su_dieu_kien",
        db_column="id_lo_thuoc",
        db_comment="Lô được khóa hoặc mở bán ở mọi chi nhánh.",
    )
    duoc_phep_ban = models.BooleanField(
        db_column="duoc_phep_ban",
        db_comment="Điều kiện bán của lô sau thao tác: true là mở bán, false là khóa bán.",
    )
    ly_do = models.TextField(
        db_column="ly_do",
        db_comment="Lý do khóa hoặc mở bán; bắt buộc khi khóa. Cho phép nhiều dòng.",
        blank=True,
        db_default="",
    )
    so_van_ban_thu_hoi = models.TextField(
        db_column="so_van_ban_thu_hoi",
        db_comment=(
            "Số công văn hoặc quyết định thu hồi của cơ quan quản lý dược, nếu khóa vì thu hồi; "
            "rỗng khi không có. Văn bản một dòng."
        ),
        blank=True,
        db_default="",
    )
    nguoi_thuc_hien = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="id_tai_khoan_thuc_hien",
        db_comment=(
            "Tài khoản khóa hoặc mở bán; NULL chỉ ở dòng ghi lại lô đã khóa trước khi có "
            "nhật ký này."
        ),
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm đổi điều kiện bán.",
        db_default=Now(),
    )

    class Meta:
        db_table = "lich_su_dieu_kien_lo"
        db_table_comment = (
            "Mỗi hàng là một lần khóa hoặc mở bán một lô; chỉ thêm, không sửa hoặc xóa."
        )
        verbose_name = "lịch sử điều kiện bán của lô"
        constraints = [
            *rang_buoc_van_ban("lich_su_dieu_kien_lo", "ly_do", rong=True, nhieu_dong=True),
            *rang_buoc_van_ban(
                "lich_su_dieu_kien_lo", "so_van_ban_thu_hoi", rong=True, nhan="so_van_ban"
            ),
            models.CheckConstraint(
                condition=models.Q(duoc_phep_ban=True) | models.Q(KhongRong("ly_do")),
                name=ten_rang_buoc("kiem_tra", "lich_su_dieu_kien_lo", "ly_do_khi_khoa"),
            ),
        ]

    def __str__(self):
        return f"{self.lo_thuoc} · {'mở bán' if self.duoc_phep_ban else 'khóa bán'}"
