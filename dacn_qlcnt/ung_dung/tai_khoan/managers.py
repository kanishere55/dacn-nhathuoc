from django.contrib.auth.base_user import BaseUserManager


class QuanLyTaiKhoan(BaseUserManager):
    use_in_migrations = True

    def create_user(self, ten_dang_nhap, password=None, **extra_fields):
        from .services import tao_tai_khoan_ky_thuat

        if extra_fields.get("la_quan_tri_he_thong", False):
            raise ValueError("Dùng create_superuser để tạo quản trị hệ thống.")
        return tao_tai_khoan_ky_thuat(
            ten_dang_nhap,
            password,
            co_so_du_lieu=self._db,
            **extra_fields,
        )

    def create_superuser(self, ten_dang_nhap, password=None, **extra_fields):
        from .services import tao_tai_khoan_ky_thuat

        extra_fields.setdefault("dang_hoat_dong", True)
        extra_fields.setdefault("la_quan_tri_he_thong", True)
        extra_fields.setdefault("vai_tro", "quan_tri_chuoi")
        if extra_fields["dang_hoat_dong"] is not True:
            raise ValueError("Quản trị hệ thống phải đang hoạt động.")
        if extra_fields["la_quan_tri_he_thong"] is not True:
            raise ValueError("Quản trị hệ thống phải có cờ quản trị hệ thống.")
        return tao_tai_khoan_ky_thuat(
            ten_dang_nhap,
            password,
            co_so_du_lieu=self._db,
            **extra_fields,
        )
