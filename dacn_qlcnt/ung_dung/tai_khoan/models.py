from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

from ung_dung.chung.van_ban import DaCatKhoangTrang, KhongRong, LaMotDong

from .managers import QuanLyTaiKhoan


class TaiKhoan(AbstractBaseUser):
    # Các thuộc tính password/last_login giữ giao diện mà Django auth cần.
    id_tai_khoan = models.BigAutoField(
        primary_key=True,
        db_column="id_tai_khoan",
        db_comment="Định danh nội bộ do PostgreSQL cấp, không phải mã hiển thị.",
    )
    ten_dang_nhap = models.TextField(
        "tên đăng nhập",
        db_column="ten_dang_nhap",
        db_comment=(
            "Tên một dòng dùng cho khung xác thực kỹ thuật giai đoạn 0; "
            "người tạo nhập. Chính sách định danh đăng nhập nghiệp vụ chưa duyệt."
        ),
    )
    password = models.CharField(
        "mật khẩu băm",
        max_length=128,
        db_column="mat_khau_bam",
        db_comment=(
            "Chuỗi băm hoặc dấu mật khẩu không sử dụng được do Django tạo; "
            "một dòng, giới hạn 128 ký tự theo AbstractBaseUser.password của Django."
        ),
    )
    dang_hoat_dong = models.BooleanField(
        "đang hoạt động",
        db_default=True,
        db_column="dang_hoat_dong",
        db_comment="Cho phép cơ chế xác thực Django nhận tài khoản; hệ thống ghi.",
    )
    la_quan_tri_he_thong = models.BooleanField(
        "là quản trị hệ thống",
        db_default=False,
        db_column="la_quan_tri_he_thong",
        db_comment=(
            "Cờ quản trị kỹ thuật tạo bằng createsuperuser; "
            "không thay thế bốn vai trò nghiệp vụ trong đề cương."
        ),
    )
    last_login = models.DateTimeField(
        "thời điểm đăng nhập cuối",
        null=True,
        blank=True,
        db_column="thoi_diem_dang_nhap_cuoi",
        db_comment=(
            "Thời điểm đăng nhập thành công gần nhất do Django cập nhật; "
            "NULL nghĩa là chưa ghi nhận lần đăng nhập."
        ),
    )

    objects = QuanLyTaiKhoan()
    USERNAME_FIELD = "ten_dang_nhap"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "tai_khoan"
        db_table_comment = (
            "Mỗi hàng là một tài khoản xác thực kỹ thuật; "
            "khung giai đoạn 0 chưa có vai trò hoặc liên kết chi nhánh nghiệp vụ."
        )
        verbose_name = "tài khoản"
        verbose_name_plural = "tài khoản"
        constraints = [
            models.UniqueConstraint(
                fields=["ten_dang_nhap"],
                name="duy_nhat__tai_khoan__ten_dang_nhap",
            ),
            models.CheckConstraint(
                condition=KhongRong("ten_dang_nhap"),
                name="kiem_tra__tai_khoan__ten_dang_nhap_khong_rong",
            ),
            models.CheckConstraint(
                condition=DaCatKhoangTrang("ten_dang_nhap"),
                name="kiem_tra__tai_khoan__ten_dang_nhap_da_cat_khoang_trang",
            ),
            models.CheckConstraint(
                condition=LaMotDong("ten_dang_nhap"),
                name="kiem_tra__tai_khoan__ten_dang_nhap_mot_dong",
            ),
            models.CheckConstraint(
                condition=KhongRong("password"),
                name="kiem_tra__tai_khoan__mat_khau_bam_khong_rong",
            ),
            models.CheckConstraint(
                condition=DaCatKhoangTrang("password"),
                name="kiem_tra__tai_khoan__mat_khau_bam_da_cat_khoang_trang",
            ),
            models.CheckConstraint(
                condition=LaMotDong("password"),
                name="kiem_tra__tai_khoan__mat_khau_bam_mot_dong",
            ),
        ]

    @property
    def is_active(self):
        return self.dang_hoat_dong

    @property
    def is_staff(self):
        return self.la_quan_tri_he_thong

    @property
    def is_superuser(self):
        return self.la_quan_tri_he_thong

    def has_perm(self, perm, obj=None):
        return self.dang_hoat_dong and self.la_quan_tri_he_thong

    def has_perms(self, perm_list, obj=None):
        return self.dang_hoat_dong and self.la_quan_tri_he_thong

    def has_module_perms(self, app_label):
        return self.dang_hoat_dong and self.la_quan_tri_he_thong

    def __str__(self):
        return self.ten_dang_nhap
