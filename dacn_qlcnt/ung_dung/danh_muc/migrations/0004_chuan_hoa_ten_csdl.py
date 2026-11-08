from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "danh_muc")


class Migration(migrations.Migration):
    dependencies = [("danh_muc", "0003_mo_rong_thong_tin_anh_va_khuyen_mai")]
    # Lùi 0003 xóa cột, bảng và ràng buộc theo cột nên bước này không cần đảo.
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
