from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "tai_khoan")


class Migration(migrations.Migration):
    dependencies = [("tai_khoan", "0008_gioi_han_dang_nhap_sai")]
    # Lùi migration này không cần đổi tên: lùi 0008 xóa cột và ràng buộc mới.
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
