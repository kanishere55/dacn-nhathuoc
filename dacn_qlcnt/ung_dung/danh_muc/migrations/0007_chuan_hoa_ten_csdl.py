from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "danh_muc")


class Migration(migrations.Migration):
    dependencies = [("danh_muc", "0006_tao_danh_gia_thuoc")]
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
