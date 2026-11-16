# Bản nộp theo đề cương (Q45): bỏ các loại thư của trả hàng, nhận tiền trực tuyến và hoàn tiền.

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ban_hang", "0018_don_dat_giu_theo_de_cuong"),
        ("thong_bao", "0011_ghi_thoi_diem_thu_lai"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="nhatkyemail",
            name="kiem_tra__nhat_ky_email__loai_email_hop_le",
        ),
        migrations.AlterField(
            model_name="nhatkyemail",
            name="loai_email",
            field=models.TextField(
                choices=[
                    ("ma_xac_thuc", "Mã xác thực"),
                    ("chao_mung", "Chào mừng tài khoản mới"),
                    ("nhac_ten_dang_nhap", "Nhắc tên đăng nhập"),
                    ("mat_khau_da_doi", "Mật khẩu đã đổi"),
                    ("email_da_doi", "Email đã đổi"),
                    ("ho_so_da_doi", "Hồ sơ đã cập nhật"),
                    ("don_hang_moi", "Xác nhận đặt giữ"),
                    ("don_hang_cap_nhat", "Cập nhật trạng thái đơn"),
                    ("xuat_hoa_don", "Yêu cầu xuất hóa đơn"),
                    ("email_da_co_tai_khoan", "Đăng ký bằng email đã có tài khoản"),
                    ("trang_thai_tai_khoan", "Khóa hoặc mở lại tài khoản"),
                ],
                db_column="loai_email",
                db_comment="Mục đích của email do hệ thống chọn khi tạo; quyết định mẫu nội dung.",
            ),
        ),
        migrations.AddConstraint(
            model_name="nhatkyemail",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "loai_email__in",
                        [
                            "ma_xac_thuc",
                            "chao_mung",
                            "nhac_ten_dang_nhap",
                            "mat_khau_da_doi",
                            "email_da_doi",
                            "ho_so_da_doi",
                            "don_hang_moi",
                            "don_hang_cap_nhat",
                            "xuat_hoa_don",
                            "email_da_co_tai_khoan",
                            "trang_thai_tai_khoan",
                        ],
                    )
                ),
                name="kiem_tra__nhat_ky_email__loai_email_hop_le",
            ),
        ),
    ]
