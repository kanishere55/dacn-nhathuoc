from django.db import connection
from django.test import TestCase

from ung_dung.chung.kiem_tra_csdl import kiem_tra_csdl


class KiemTraCsdlTests(TestCase):
    def test_schema_dat_va_phat_hien_cot_them_ngoai_migration(self):
        so_bang, cac_loi, cac_canh_bao = kiem_tra_csdl(connection)
        self.assertGreater(so_bang, 0)
        self.assertEqual(cac_loi, [])
        self.assertEqual(cac_canh_bao, [])

        with connection.cursor() as con_tro:
            con_tro.execute("ALTER TABLE tai_khoan ADD COLUMN cot_moi integer")
        _, cac_loi, _ = kiem_tra_csdl(connection)
        self.assertTrue(
            any(loi.startswith("L03 tai_khoan") and "cot_moi" in loi for loi in cac_loi)
        )
