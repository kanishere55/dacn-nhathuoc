from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "tai_khoan")


def khoi_phuc(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "tai_khoan", dao=True)


class Migration(migrations.Migration):
    dependencies = [("tai_khoan", "0010_so_dien_thoai_viet_nam")]
    operations = [migrations.RunPython(chuan_hoa, khoi_phuc)]
