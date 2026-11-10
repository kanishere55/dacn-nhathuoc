from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "tai_khoan")


class Migration(migrations.Migration):
    dependencies = [("tai_khoan", "0006_tao_nhom_quyen")]
    # Lùi migration này không cần đổi tên: lùi 0006 xóa bảng và ràng buộc theo bảng.
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
