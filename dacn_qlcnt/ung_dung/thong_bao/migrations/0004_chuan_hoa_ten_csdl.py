from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "thong_bao")


class Migration(migrations.Migration):
    dependencies = [("thong_bao", "0003_them_loai_email_don_hang")]
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
