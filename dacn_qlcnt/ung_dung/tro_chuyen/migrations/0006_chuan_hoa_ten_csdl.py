from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "tro_chuyen")


def khoi_phuc(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "tro_chuyen", dao=True)


class Migration(migrations.Migration):
    dependencies = [("tro_chuyen", "0005_trang_thai_va_tin_cuoi")]
    operations = [migrations.RunPython(chuan_hoa, khoi_phuc)]
