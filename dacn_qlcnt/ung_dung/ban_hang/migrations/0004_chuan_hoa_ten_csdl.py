from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "ban_hang")


class Migration(migrations.Migration):
    dependencies = [("ban_hang", "0003_hop_nhat_don_hang")]
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
