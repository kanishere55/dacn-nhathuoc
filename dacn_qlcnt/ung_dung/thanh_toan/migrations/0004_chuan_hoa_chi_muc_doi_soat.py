from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "thanh_toan")


class Migration(migrations.Migration):
    dependencies = [("thanh_toan", "0003_doi_soat_ban_hang")]
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
