from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "tai_khoan")


def khoi_phuc(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "tai_khoan", dao=True)


class Migration(migrations.Migration):
    dependencies = [("tai_khoan", "0002_them_vai_tro_va_chi_nhanh")]
    operations = [migrations.RunPython(chuan_hoa, khoi_phuc)]
