from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "ban_hang")


def khoi_phuc(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "ban_hang", dao=True)


class Migration(migrations.Migration):
    dependencies = [("ban_hang", "0001_tao_ban_hang_va_dat_giu")]
    operations = [migrations.RunPython(chuan_hoa, khoi_phuc)]
