from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "kho")


class Migration(migrations.Migration):
    dependencies = [("kho", "0003_tao_phieu_xuat_huy")]
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
