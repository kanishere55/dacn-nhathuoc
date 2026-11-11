from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "thong_bao")


class Migration(migrations.Migration):
    dependencies = [("thong_bao", "0009_luu_ban_html_va_gui_lai")]
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
