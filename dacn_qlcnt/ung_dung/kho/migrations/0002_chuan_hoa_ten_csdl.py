from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "kho")


def khoi_phuc(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "kho", dao=True)


class Migration(migrations.Migration):
    dependencies = [("kho", "0001_tao_cac_chung_tu_kho")]
    operations = [migrations.RunPython(chuan_hoa, khoi_phuc)]
