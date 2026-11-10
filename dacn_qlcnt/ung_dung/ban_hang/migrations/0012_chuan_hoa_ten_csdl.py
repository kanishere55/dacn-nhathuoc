from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "ban_hang")


class Migration(migrations.Migration):
    dependencies = [("ban_hang", "0011_tra_hang_noi_nhan_tien_va_nhap_lai_kho")]
    # Lùi migration này không cần đổi tên: lùi 0011 xóa bảng, cột và ràng buộc theo cột.
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
