from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "danh_muc")


def khoi_phuc(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "danh_muc", dao=True)


class Migration(migrations.Migration):
    dependencies = [("danh_muc", "0001_tao_danh_muc")]
    operations = [migrations.RunPython(chuan_hoa, khoi_phuc)]
