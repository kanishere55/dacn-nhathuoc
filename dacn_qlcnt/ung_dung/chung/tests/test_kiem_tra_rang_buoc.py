from django.db import connection
from django.test import TestCase

from ung_dung.chung.tests.kiem_tra_rang_buoc import (
    LoiBoKiemTra,
    LoiCaKiemTra,
    kiem_tra_ca_dung,
    kiem_tra_ca_sai,
)

CAU_LENH_GHI = "INSERT INTO mau_bo_kiem_tra (ma_mau, ten_mau) VALUES (%s, %s)"
TEN_RANG_BUOC = "kiem_tra__mau_bo_kiem_tra__ten_khong_rong"


class TuKiemBoThuRangBuocTests(TestCase):
    def setUp(self):
        with connection.cursor() as con_tro:
            con_tro.execute(
                """
                CREATE TEMPORARY TABLE mau_bo_kiem_tra (
                    ma_mau text NOT NULL,
                    ten_mau text NOT NULL,
                    CONSTRAINT khoa_chinh__mau_bo_kiem_tra PRIMARY KEY (ma_mau),
                    CONSTRAINT kiem_tra__mau_bo_kiem_tra__ten_khong_rong
                        CHECK (public.khong_rong(ten_mau))
                ) ON COMMIT DROP
                """
            )

    def test_sai_cu_phap_la_loi_bo_test(self):
        with connection.cursor() as con_tro, self.assertRaises(LoiBoKiemTra):
            kiem_tra_ca_sai(con_tro, "SELLECT 1", None, "23514", TEN_RANG_BUOC)

    def test_bang_khong_ton_tai_la_loi_bo_test(self):
        with connection.cursor() as con_tro, self.assertRaises(LoiBoKiemTra):
            kiem_tra_ca_sai(
                con_tro,
                "INSERT INTO bang_khong_ton_tai_cho_tu_kiem (ten_mau) VALUES ('a')",
                None,
                "23514",
                TEN_RANG_BUOC,
            )

    def test_khong_duoc_khai_bao_syntax_error_la_ket_qua_mong_doi(self):
        with connection.cursor() as con_tro, self.assertRaises(LoiBoKiemTra):
            kiem_tra_ca_sai(con_tro, "SELLECT 1", None, "42601", None)

    def test_sqlstate_sai_khong_duoc_cham_dat(self):
        with connection.cursor() as con_tro, self.assertRaises(LoiBoKiemTra):
            kiem_tra_ca_sai(con_tro, CAU_LENH_GHI, ("MA_SAI_STATE", ""), "23505", TEN_RANG_BUOC)

    def test_dung_sqlstate_nhung_sai_rang_buoc_khong_duoc_cham_dat(self):
        with connection.cursor() as con_tro, self.assertRaises(LoiCaKiemTra):
            kiem_tra_ca_sai(
                con_tro,
                CAU_LENH_GHI,
                ("MA_SAI_TEN", ""),
                "23514",
                "kiem_tra__mau_bo_kiem_tra__ten_mot_dong",
            )

    def test_du_lieu_sai_van_duoc_nhan_thi_ca_thu_that_bai_va_rollback(self):
        with connection.cursor() as con_tro:
            with self.assertRaises(LoiCaKiemTra):
                kiem_tra_ca_sai(
                    con_tro, CAU_LENH_GHI, ("MA_KHONG_BI_CHAN", "An Bình"), "23514", TEN_RANG_BUOC
                )
            con_tro.execute(
                "SELECT count(*) FROM mau_bo_kiem_tra WHERE ma_mau = %s", ("MA_KHONG_BI_CHAN",)
            )
            self.assertEqual(con_tro.fetchone(), (0,))

    def test_ca_dung_khong_ghi_dong_nao_thi_that_bai(self):
        with connection.cursor() as con_tro, self.assertRaises(LoiCaKiemTra):
            kiem_tra_ca_dung(
                con_tro,
                "UPDATE mau_bo_kiem_tra SET ten_mau = %s WHERE ma_mau = %s",
                ("An Bình", "MA_CHUA_CO"),
            )

    def test_select_khong_duoc_coi_la_ca_ghi_dung(self):
        with connection.cursor() as con_tro, self.assertRaises(LoiCaKiemTra):
            kiem_tra_ca_dung(con_tro, "SELECT 1")

    def test_ca_dung_bi_chan_thi_that_bai(self):
        with connection.cursor() as con_tro, self.assertRaises(LoiCaKiemTra):
            kiem_tra_ca_dung(con_tro, CAU_LENH_GHI, ("MA_DUNG_BI_CHAN", ""))

    def test_tap_ten_rang_buoc_duoc_chap_nhan(self):
        with connection.cursor() as con_tro:
            kiem_tra_ca_sai(
                con_tro,
                CAU_LENH_GHI,
                ("MA_TAP_TEN", ""),
                "23514",
                {TEN_RANG_BUOC, "kiem_tra__mau_bo_kiem_tra__ten_mot_dong"},
            )

    def test_ca_dung_that_su_ghi_duoc_mot_dong(self):
        with connection.cursor() as con_tro:
            kiem_tra_ca_dung(con_tro, CAU_LENH_GHI, ("MA_HOP_LE", "An Bình"))
            con_tro.execute("SELECT ten_mau FROM mau_bo_kiem_tra WHERE ma_mau = %s", ("MA_HOP_LE",))
            self.assertEqual(con_tro.fetchone(), ("An Bình",))
