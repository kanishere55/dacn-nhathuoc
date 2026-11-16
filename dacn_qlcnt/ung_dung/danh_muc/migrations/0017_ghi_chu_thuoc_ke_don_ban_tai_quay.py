# Thuốc kê đơn: bỏ câu "không bán giao hàng" khỏi chú thích cột (bản nộp theo đề cương, Q45).

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("danh_muc", "0016_gioi_han_phan_tram_khuyen_mai"),
    ]

    operations = [
        migrations.AlterField(
            model_name="thuoc",
            name="la_thuoc_ke_don",
            field=models.BooleanField(
                db_column="la_thuoc_ke_don",
                db_comment="Thuốc phải bán theo đơn; chỉ bán tại quầy khi dược sĩ đã kiểm tra đơn thuốc (Luật số 44/2024/QH15).",
                db_default=False,
                default=False,
            ),
        ),
    ]
