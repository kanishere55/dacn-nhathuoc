from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now

from ung_dung.chung.ten_csdl import EMAIL, rang_buoc_van_ban, ten_rang_buoc

BANG = "nhat_ky_email"
LOAI_EMAIL = [
    ("ma_xac_thuc", "Mã xác thực"),
    ("chao_mung", "Chào mừng tài khoản mới"),
    ("nhac_ten_dang_nhap", "Nhắc tên đăng nhập"),
    ("mat_khau_da_doi", "Mật khẩu đã đổi"),
    ("email_da_doi", "Email đã đổi"),
    ("ho_so_da_doi", "Hồ sơ đã cập nhật"),
]
TRANG_THAI = [("cho_gui", "Chờ gửi"), ("da_gui", "Đã gửi"), ("loi", "Gửi lỗi")]


class NhatKyEmail(models.Model):
    id_nhat_ky_email = models.BigAutoField(
        primary_key=True,
        db_column="id_nhat_ky_email",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
    )
    loai_email = models.TextField(
        choices=LOAI_EMAIL,
        db_column="loai_email",
        db_comment="Mục đích của email do hệ thống chọn khi tạo; quyết định mẫu nội dung.",
    )
    email_nhan = models.TextField(
        db_column="email_nhan",
        db_comment="Địa chỉ người nhận đã chuẩn hóa chữ thường tại thời điểm gửi.",
    )
    tai_khoan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="id_tai_khoan",
        db_comment="Tài khoản liên quan; NULL khi email gửi trước lúc có tài khoản.",
    )
    tieu_de = models.TextField(
        db_column="tieu_de", db_comment="Tiêu đề email đã gửi; văn bản một dòng."
    )
    noi_dung_van_ban = models.TextField(
        db_column="noi_dung_van_ban",
        db_comment=(
            "Bản văn bản thuần của email để đối chiếu; mã OTP và khóa bí mật được che "
            "trước khi lưu."
        ),
    )
    trang_thai = models.TextField(
        choices=TRANG_THAI,
        db_default="cho_gui",
        db_column="trang_thai",
        db_comment="cho_gui khi transaction chưa xong, da_gui khi máy chủ SMTP nhận, loi khi lỗi.",
    )
    chi_tiet_loi = models.TextField(
        blank=True,
        db_default="",
        db_column="chi_tiet_loi",
        db_comment="Thông báo lỗi một dòng từ máy chủ SMTP; rỗng khi không lỗi.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_default=Now(),
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận yêu cầu gửi email.",
    )
    thoi_diem_gui = models.DateTimeField(
        null=True,
        blank=True,
        db_column="thoi_diem_gui",
        db_comment="Thời điểm máy chủ SMTP nhận email; NULL khi chưa gửi được.",
    )

    class Meta:
        db_table = BANG
        db_table_comment = "Mỗi hàng là một email hệ thống đã tạo, kèm kết quả gửi."
        verbose_name = "nhật ký email"
        verbose_name_plural = "nhật ký email"
        ordering = ["-thoi_diem_tao", "-id_nhat_ky_email"]
        indexes = [
            models.Index(
                fields=["thoi_diem_tao"], name=ten_rang_buoc("chi_muc", BANG, "thoi_diem_tao")
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(loai_email__in=[ma for ma, _ in LOAI_EMAIL]),
                name=ten_rang_buoc("kiem_tra", BANG, "loai_email_hop_le"),
            ),
            models.CheckConstraint(
                condition=Q(trang_thai__in=[ma for ma, _ in TRANG_THAI]),
                name=ten_rang_buoc("kiem_tra", BANG, "trang_thai_hop_le"),
            ),
            *rang_buoc_van_ban(BANG, "email_nhan", dinh_dang=EMAIL),
            *rang_buoc_van_ban(BANG, "tieu_de"),
            *rang_buoc_van_ban(BANG, "noi_dung_van_ban", nhieu_dong=True),
            *rang_buoc_van_ban(BANG, "chi_tiet_loi", rong=True),
            models.CheckConstraint(
                condition=(
                    Q(trang_thai="da_gui", thoi_diem_gui__isnull=False, chi_tiet_loi="")
                    | Q(trang_thai="loi", thoi_diem_gui__isnull=True)
                    | Q(trang_thai="cho_gui", thoi_diem_gui__isnull=True, chi_tiet_loi="")
                ),
                name=ten_rang_buoc("kiem_tra", BANG, "ket_qua_dung_trang_thai"),
            ),
            models.CheckConstraint(
                condition=Q(trang_thai="da_gui") | Q(trang_thai="cho_gui") | ~Q(chi_tiet_loi=""),
                name=ten_rang_buoc("kiem_tra", BANG, "loi_co_chi_tiet"),
            ),
        ]

    def __str__(self):
        return f"{self.get_loai_email_display()} → {self.email_nhan}"
