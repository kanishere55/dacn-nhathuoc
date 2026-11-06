from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "du_bao")


def khoi_phuc(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "du_bao", dao=True)


class Migration(migrations.Migration):
    dependencies = [("du_bao", "0001_tao_thuc_nghiem_du_bao")]
    operations = [migrations.RunPython(chuan_hoa, khoi_phuc)]
