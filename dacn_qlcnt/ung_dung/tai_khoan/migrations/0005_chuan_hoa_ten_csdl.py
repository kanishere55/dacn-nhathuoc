from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "tai_khoan")


class Migration(migrations.Migration):
    dependencies = [("tai_khoan", "0004_them_ho_so_dia_chi_va_xac_thuc")]
    # Lùi migration này không cần đổi tên: lùi 0004 xóa cột và ràng buộc theo cột.
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
