from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase


class DiTruQuanTriTests(TransactionTestCase):
    def test_quan_tri_giai_doan_0_duoc_chuyen_thanh_quan_tri_chuoi(self):
        try:
            call_command("migrate", "tai_khoan", "0001", verbosity=0, interactive=False)
            with connection.cursor() as con_tro:
                con_tro.execute(
                    """
                    INSERT INTO tai_khoan (ten_dang_nhap, mat_khau_bam, la_quan_tri_he_thong)
                    VALUES (%s, %s, TRUE)
                    """,
                    ["quan_tri_cu", "!"],
                )
        finally:
            call_command("migrate", verbosity=0, interactive=False)
        tai_khoan = get_user_model().objects.get(ten_dang_nhap="quan_tri_cu")
        self.assertEqual(tai_khoan.vai_tro, "quan_tri_chuoi")
        self.assertTrue(tai_khoan.la_quan_tri_he_thong)
