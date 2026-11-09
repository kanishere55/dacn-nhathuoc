from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "noi_dung")


class Migration(migrations.Migration):
    dependencies = [("noi_dung", "0003_tao_tin_tuc")]
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
