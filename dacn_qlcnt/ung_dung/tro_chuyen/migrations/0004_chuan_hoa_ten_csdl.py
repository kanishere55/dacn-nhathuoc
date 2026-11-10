from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "tro_chuyen")


def khoi_phuc(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "tro_chuyen", dao=True)


class Migration(migrations.Migration):
    dependencies = [("tro_chuyen", "0003_phan_loai_va_da_doc")]
    operations = [migrations.RunPython(chuan_hoa, khoi_phuc)]
