from django.db import connection
from django.test import SimpleTestCase, TestCase

from ung_dung.chung.tests.kiem_tra_rang_buoc import (
    kiem_tra_ca_dung,
    kiem_tra_ca_sai,
)
from ung_dung.chung.van_ban import (
    MA_CAM_MOT_DONG,
    MA_KHOANG_TRANG,
    cat_khoang_trang,
    la_mot_dong,
)

KHONG_RONG = "kiem_tra__mau_van_ban__ten_khong_rong"
DA_CAT = "kiem_tra__mau_van_ban__ten_da_cat_khoang_trang"
MOT_DONG = "kiem_tra__mau_van_ban__ten_mot_dong"
CAU_LENH_GHI = "INSERT INTO mau_van_ban (ma_mau, ten_mau) VALUES (%s, %s)"


class ChuanHoaVanBanTests(SimpleTestCase):
    def test_tap_ky_tu_khong_thieu_hoac_trung(self):
        self.assertEqual(len(MA_KHOANG_TRANG), 27)
        self.assertEqual(len(set(MA_KHOANG_TRANG)), 27)
        self.assertEqual(len(MA_CAM_MOT_DONG), 66)
        self.assertEqual(len(set(MA_CAM_MOT_DONG)), 66)

    def test_cat_tung_ky_tu_khoang_trang_o_dau_va_cuoi(self):
        for ma in MA_KHOANG_TRANG:
            with self.subTest(ma=f"U+{ma:04X}"):
                self.assertEqual(cat_khoang_trang(chr(ma) + "An Bình" + chr(ma)), "An Bình")
                self.assertEqual(cat_khoang_trang(chr(ma) * 2), "")

    def test_khong_xoa_ky_tu_o_giua(self):
        for ma in MA_KHOANG_TRANG:
            with self.subTest(ma=f"U+{ma:04X}"):
                van_ban = "An" + chr(ma) + "Bình"
                self.assertEqual(cat_khoang_trang(van_ban), van_ban)

    def test_tu_choi_tung_ky_tu_cam_mot_dong(self):
        for ma in MA_CAM_MOT_DONG:
            with self.subTest(ma=f"U+{ma:04X}"):
                self.assertFalse(la_mot_dong("An" + chr(ma) + "Bình"))

    def test_giu_nguyen_van_ban_tieng_viet_va_ky_tu_ngoai_tap(self):
        for van_ban in ("", "Nhà thuốc An Bình", "Dược phẩm 💊", "An\u180eBình", "An\u200dBình"):
            with self.subTest(van_ban=van_ban):
                self.assertEqual(cat_khoang_trang(van_ban), van_ban)
                self.assertTrue(la_mot_dong(van_ban))


class HamVanBanPostgreSQLTests(TestCase):
    def setUp(self):
        with connection.cursor() as con_tro:
            con_tro.execute(
                """
                CREATE TEMPORARY TABLE mau_van_ban (
                    ma_mau text NOT NULL,
                    ten_mau text NOT NULL,
                    CONSTRAINT khoa_chinh__mau_van_ban PRIMARY KEY (ma_mau),
                    CONSTRAINT kiem_tra__mau_van_ban__ten_khong_rong
                        CHECK (public.khong_rong(ten_mau)),
                    CONSTRAINT kiem_tra__mau_van_ban__ten_da_cat_khoang_trang
                        CHECK (public.da_cat_khoang_trang(ten_mau)),
                    CONSTRAINT kiem_tra__mau_van_ban__ten_mot_dong
                        CHECK (public.la_mot_dong(ten_mau))
                ) ON COMMIT DROP
                """
            )

    def test_ham_khai_bao_immutable_strict_parallel_safe_va_co_chu_thich(self):
        with connection.cursor() as con_tro:
            con_tro.execute(
                """
                SELECT proname, provolatile, proisstrict, proparallel,
                       obj_description(oid, 'pg_proc')
                FROM pg_proc
                WHERE oid IN (
                    'public.khong_rong(text)'::regprocedure,
                    'public.da_cat_khoang_trang(text)'::regprocedure,
                    'public.la_mot_dong(text)'::regprocedure
                )
                """
            )
            cac_ham = con_tro.fetchall()
        self.assertEqual(len(cac_ham), 3)
        for ten, tinh_bat_bien, strict, song_song, chu_thich in cac_ham:
            with self.subTest(ten=ten):
                self.assertEqual(tinh_bat_bien, "i")
                self.assertTrue(strict)
                self.assertEqual(song_song, "s")
                self.assertIn("không tự kiểm lại dữ liệu cũ", chu_thich)

    def test_null_tra_null_va_not_null_van_duoc_bao_ve(self):
        with connection.cursor() as con_tro:
            con_tro.execute(
                "SELECT public.khong_rong(NULL), "
                "public.da_cat_khoang_trang(NULL), public.la_mot_dong(NULL)"
            )
            self.assertEqual(con_tro.fetchone(), (None, None, None))
            kiem_tra_ca_sai(con_tro, CAU_LENH_GHI, ("MA_NULL", None), "23502", None)

    def test_chuoi_rong_chi_vi_pham_quy_tac_khong_rong(self):
        with connection.cursor() as con_tro:
            con_tro.execute(
                "SELECT public.khong_rong(''), "
                "public.da_cat_khoang_trang(''), public.la_mot_dong('')"
            )
            self.assertEqual(con_tro.fetchone(), (False, True, True))
            kiem_tra_ca_sai(con_tro, CAU_LENH_GHI, ("MA_RONG", ""), "23514", KHONG_RONG)

    def test_moi_khoang_trang_bi_chan_khi_dung_mot_minh_hoac_o_hai_dau(self):
        with connection.cursor() as con_tro:
            for ma in MA_KHOANG_TRANG:
                ky_tu = chr(ma)
                rang_buoc = {KHONG_RONG, DA_CAT}
                if ma in MA_CAM_MOT_DONG:
                    rang_buoc.add(MOT_DONG)
                with self.subTest(ma=f"U+{ma:04X}", vi_tri="mot_minh"):
                    kiem_tra_ca_sai(
                        con_tro, CAU_LENH_GHI, (f"MA_RONG_{ma:X}", ky_tu), "23514", rang_buoc
                    )
                for ten_vi_tri, ten in (("dau", ky_tu + "An Bình"), ("cuoi", "An Bình" + ky_tu)):
                    with self.subTest(ma=f"U+{ma:04X}", vi_tri=ten_vi_tri):
                        rang_buoc_dau_cuoi = {DA_CAT}
                        if ma in MA_CAM_MOT_DONG:
                            rang_buoc_dau_cuoi.add(MOT_DONG)
                        kiem_tra_ca_sai(
                            con_tro,
                            CAU_LENH_GHI,
                            (f"MA_{ten_vi_tri}_{ma:X}", ten),
                            "23514",
                            rang_buoc_dau_cuoi,
                        )

    def test_moi_ky_tu_cam_o_giua_bi_chan_boi_check_mot_dong(self):
        with connection.cursor() as con_tro:
            for ma in MA_CAM_MOT_DONG:
                with self.subTest(ma=f"U+{ma:04X}"):
                    kiem_tra_ca_sai(
                        con_tro,
                        CAU_LENH_GHI,
                        (f"MA_CAM_{ma:X}", "An" + chr(ma) + "Bình"),
                        "23514",
                        MOT_DONG,
                    )

    def test_python_va_sql_cung_dinh_nghia_khoang_trang_va_mot_dong(self):
        cac_van_ban = ["", "An Bình", "💊", "An\u180eBình", "An\u200dBình"]
        for ma in set(MA_KHOANG_TRANG) | set(MA_CAM_MOT_DONG):
            cac_van_ban.extend((chr(ma), chr(ma) + "An Bình", "An" + chr(ma) + "Bình"))
        with connection.cursor() as con_tro:
            for van_ban in cac_van_ban:
                with self.subTest(van_ban=repr(van_ban)):
                    con_tro.execute(
                        "SELECT public.khong_rong(%s), "
                        "public.da_cat_khoang_trang(%s), public.la_mot_dong(%s)",
                        (van_ban, van_ban, van_ban),
                    )
                    self.assertEqual(
                        con_tro.fetchone(),
                        (
                            bool(cat_khoang_trang(van_ban)),
                            cat_khoang_trang(van_ban) == van_ban,
                            la_mot_dong(van_ban),
                        ),
                    )

    def test_van_ban_dung_duoc_ghi_va_tra_cuu_theo_ma(self):
        with connection.cursor() as con_tro:
            for ma_mau, ten in (
                ("MA_VIET", "Nhà thuốc An Bình"),
                ("MA_ASCII", "Nha thuoc An Binh"),
                ("MA_EMOJI", "Dược phẩm 💊"),
                ("MA_SAU_CHUAN_HOA", cat_khoang_trang("\u200b An Bình \ufeff")),
            ):
                with self.subTest(ma_mau=ma_mau):
                    kiem_tra_ca_dung(con_tro, CAU_LENH_GHI, (ma_mau, ten))
                    con_tro.execute("SELECT ten_mau FROM mau_van_ban WHERE ma_mau = %s", (ma_mau,))
                    self.assertEqual(con_tro.fetchone(), (ten,))
