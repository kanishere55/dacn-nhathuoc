from django.db import migrations, models

import ung_dung.chung.van_ban
import ung_dung.tai_khoan.managers


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("chung", "0001_tao_ham_kiem_van_ban"),
    ]

    operations = [
        migrations.CreateModel(
            name="TaiKhoan",
            fields=[
                (
                    "id_tai_khoan",
                    models.BigAutoField(
                        db_column="id_tai_khoan",
                        db_comment="Định danh nội bộ do PostgreSQL cấp, không phải mã hiển thị.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "ten_dang_nhap",
                    models.TextField(
                        db_column="ten_dang_nhap",
                        db_comment="Tên một dòng dùng cho khung xác thực kỹ thuật giai đoạn 0; người tạo nhập. Chính sách định danh đăng nhập nghiệp vụ chưa duyệt.",
                        verbose_name="tên đăng nhập",
                    ),
                ),
                (
                    "password",
                    models.CharField(
                        db_column="mat_khau_bam",
                        db_comment="Chuỗi băm hoặc dấu mật khẩu không sử dụng được do Django tạo; một dòng, giới hạn 128 ký tự theo AbstractBaseUser.password của Django.",
                        max_length=128,
                        verbose_name="mật khẩu băm",
                    ),
                ),
                (
                    "dang_hoat_dong",
                    models.BooleanField(
                        db_column="dang_hoat_dong",
                        db_comment="Cho phép cơ chế xác thực Django nhận tài khoản; hệ thống ghi.",
                        db_default=True,
                        verbose_name="đang hoạt động",
                    ),
                ),
                (
                    "la_quan_tri_he_thong",
                    models.BooleanField(
                        db_column="la_quan_tri_he_thong",
                        db_comment="Cờ quản trị kỹ thuật tạo bằng createsuperuser; không thay thế bốn vai trò nghiệp vụ trong đề cương.",
                        db_default=False,
                        verbose_name="là quản trị hệ thống",
                    ),
                ),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True,
                        db_column="thoi_diem_dang_nhap_cuoi",
                        db_comment="Thời điểm đăng nhập thành công gần nhất do Django cập nhật; NULL nghĩa là chưa ghi nhận lần đăng nhập.",
                        null=True,
                        verbose_name="thời điểm đăng nhập cuối",
                    ),
                ),
            ],
            options={
                "verbose_name": "tài khoản",
                "verbose_name_plural": "tài khoản",
                "db_table": "tai_khoan",
                "db_table_comment": "Mỗi hàng là một tài khoản xác thực kỹ thuật; khung giai đoạn 0 chưa có vai trò hoặc liên kết chi nhánh nghiệp vụ.",
            },
            managers=[
                ("objects", ung_dung.tai_khoan.managers.QuanLyTaiKhoan()),
            ],
        ),
        # db_default khiến Django có thể hoãn CHECK đến cuối migration; tách thao tác
        # để ràng buộc thật sự tồn tại trước khi COMMENT ON CONSTRAINT chạy.
        migrations.AddConstraint(
            model_name="taikhoan",
            constraint=models.UniqueConstraint(
                fields=("ten_dang_nhap",), name="duy_nhat__tai_khoan__ten_dang_nhap"
            ),
        ),
        migrations.AddConstraint(
            model_name="taikhoan",
            constraint=models.CheckConstraint(
                condition=ung_dung.chung.van_ban.KhongRong("ten_dang_nhap"),
                name="kiem_tra__tai_khoan__ten_dang_nhap_khong_rong",
            ),
        ),
        migrations.AddConstraint(
            model_name="taikhoan",
            constraint=models.CheckConstraint(
                condition=ung_dung.chung.van_ban.DaCatKhoangTrang("ten_dang_nhap"),
                name="kiem_tra__tai_khoan__ten_dang_nhap_da_cat_khoang_trang",
            ),
        ),
        migrations.AddConstraint(
            model_name="taikhoan",
            constraint=models.CheckConstraint(
                condition=ung_dung.chung.van_ban.LaMotDong("ten_dang_nhap"),
                name="kiem_tra__tai_khoan__ten_dang_nhap_mot_dong",
            ),
        ),
        migrations.AddConstraint(
            model_name="taikhoan",
            constraint=models.CheckConstraint(
                condition=ung_dung.chung.van_ban.KhongRong("password"),
                name="kiem_tra__tai_khoan__mat_khau_bam_khong_rong",
            ),
        ),
        migrations.AddConstraint(
            model_name="taikhoan",
            constraint=models.CheckConstraint(
                condition=ung_dung.chung.van_ban.DaCatKhoangTrang("password"),
                name="kiem_tra__tai_khoan__mat_khau_bam_da_cat_khoang_trang",
            ),
        ),
        migrations.AddConstraint(
            model_name="taikhoan",
            constraint=models.CheckConstraint(
                condition=ung_dung.chung.van_ban.LaMotDong("password"),
                name="kiem_tra__tai_khoan__mat_khau_bam_mot_dong",
            ),
        ),
        migrations.RunSQL(
            sql=(
                "ALTER TABLE tai_khoan RENAME CONSTRAINT tai_khoan_pkey TO khoa_chinh__tai_khoan;"
            ),
            reverse_sql=(
                "ALTER TABLE tai_khoan RENAME CONSTRAINT khoa_chinh__tai_khoan TO tai_khoan_pkey;"
            ),
        ),
        migrations.RunSQL(
            sql="""
                COMMENT ON CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_khong_rong
                    ON tai_khoan IS 'Tên phải có ký tự ngoài tập khoảng trắng cố định; hàm STRICT đi cùng NOT NULL.';
                COMMENT ON CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_da_cat_khoang_trang
                    ON tai_khoan IS 'Hai đầu tên không có khoảng trắng theo đúng tập Unicode của hàm DB, không phụ thuộc locale.';
                COMMENT ON CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_mot_dong
                    ON tai_khoan IS 'Tên không chứa ký tự điều khiển hoặc ngắt dòng U+2028/U+2029.';
                COMMENT ON CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_khong_rong
                    ON tai_khoan IS 'Chuỗi do cơ chế mật khẩu Django tạo phải có ký tự ngoài tập khoảng trắng.';
                COMMENT ON CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_da_cat_khoang_trang
                    ON tai_khoan IS 'Chuỗi mật khẩu băm không có khoảng trắng hai đầu theo tập Unicode cố định.';
                COMMENT ON CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_mot_dong
                    ON tai_khoan IS 'Chuỗi mật khẩu băm không chứa ký tự điều khiển hoặc ngắt dòng.';
            """,
            reverse_sql="""
                COMMENT ON CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_khong_rong ON tai_khoan IS NULL;
                COMMENT ON CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_da_cat_khoang_trang ON tai_khoan IS NULL;
                COMMENT ON CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_mot_dong ON tai_khoan IS NULL;
                COMMENT ON CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_khong_rong ON tai_khoan IS NULL;
                COMMENT ON CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_da_cat_khoang_trang ON tai_khoan IS NULL;
                COMMENT ON CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_mot_dong ON tai_khoan IS NULL;
            """,
        ),
    ]
