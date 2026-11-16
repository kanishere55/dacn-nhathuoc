"""Bản nộp: không còn hàng khách trả chờ hủy nên mọi phiếu xuất hủy đều trừ tồn (Q45)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("kho", "0008_phan_biet_phieu_huy_da_xuat"),
        # Chặn trước CSDL của bản đầy đủ (có phiếu hủy hàng trả) rồi mới bỏ cột.
        ("ban_hang", "0017_kiem_tra_csdl_ban_nop"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="phieuxuathuy",
            name="co_tru_ton",
        ),
    ]
