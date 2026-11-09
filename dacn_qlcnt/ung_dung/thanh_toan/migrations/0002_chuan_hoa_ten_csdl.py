from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "thanh_toan")


def khoi_phuc(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "thanh_toan", dao=True)


class Migration(migrations.Migration):
    dependencies = [("thanh_toan", "0001_tao_giao_dich_thanh_toan")]
    operations = [migrations.RunPython(chuan_hoa, khoi_phuc)]
