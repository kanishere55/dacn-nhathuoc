from django.db import connection
from django.test import TestCase

from ung_dung.chung.tests.kiem_tra_rang_buoc import kiem_tra_ca_dung, kiem_tra_ca_sai

CHEN = "INSERT INTO tai_khoan (ten_dang_nhap, mat_khau_bam, email, so_dien_thoai, da_xac_thuc_email) VALUES (%s, '!', %s, %s, %s)"


class RangBuocHoSoTests(TestCase):
    def test_email_va_so_dien_thoai(self):
        with connection.cursor() as con_tro:
            kiem_tra_ca_dung(con_tro, CHEN, ["a1", "a@b.vn", "0901234567", True])
            kiem_tra_ca_dung(con_tro, CHEN, ["a2", None, "", False])
            kiem_tra_ca_sai(
                con_tro,
                CHEN,
                ["a3", "A@b.vn", "", False],
                "23514",
                "kiem_tra__tai_khoan__email_dung_dinh_dang",
            )
            kiem_tra_ca_sai(
                con_tro, CHEN, ["a4", "a@b.vn", "", False], "23505", "duy_nhat__tai_khoan__email"
            )
            kiem_tra_ca_sai(
                con_tro,
                CHEN,
                ["a5", None, "", True],
                "23514",
                "kiem_tra__tai_khoan__xac_thuc_can_email",
            )
            kiem_tra_ca_sai(
                con_tro,
                CHEN,
                ["a6", None, "+84901234567", False],
                "23514",
                "kiem_tra__tai_khoan__so_dien_thoai_dung_dinh_dang",
            )

    def test_phien_dang_ky_phai_co_du_lieu(self):
        cau = (
            "INSERT INTO phien_xac_thuc (ma_phien_xac_thuc, loai_xac_thuc, email, bam_otp, "
            "thoi_diem_gui_cuoi, thoi_diem_het_han, ten_dang_nhap_dang_ky) "
            "VALUES (gen_random_uuid()::text, %s, 'a@b.vn', repeat('a', 64), now(), "
            "now() + interval '10 minutes', %s)"
        )
        with connection.cursor() as con_tro:
            kiem_tra_ca_dung(con_tro, cau, ["quen_mat_khau", ""])
            kiem_tra_ca_sai(
                con_tro,
                cau,
                ["dang_ky", ""],
                "23514",
                "kiem_tra__xac_thuc__du_lieu_dang_ky_dung_loai",
            )
            kiem_tra_ca_sai(
                con_tro,
                cau,
                ["quen_mat_khau", "ten"],
                "23514",
                "kiem_tra__xac_thuc__du_lieu_dang_ky_dung_loai",
            )
