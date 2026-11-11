from django.db import migrations

from ung_dung.chung.ten_csdl import chuan_hoa_v1


def chuan_hoa(apps, schema_editor):
    chuan_hoa_v1(apps, schema_editor, "tai_khoan")


class Migration(migrations.Migration):
    dependencies = [("tai_khoan", "0012_ghi_ip_va_khoi_phuc_email")]
    operations = [migrations.RunPython(chuan_hoa, migrations.RunPython.noop)]
