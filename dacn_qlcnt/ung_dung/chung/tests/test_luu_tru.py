from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import models
from django.test import SimpleTestCase, override_settings
from django.test.utils import isolate_apps

from ung_dung.chung.kiem_tra_luu_tru import (
    DUOI_TEP_ANH,
    DUOI_TEP_DU_LIEU,
    THU_MUC_BO_QUA,
    kiem_tra_luu_tru,
    tim_tep_du_lieu,
)


class KiemTraLuuTruTests(SimpleTestCase):
    def setUp(self):
        self.thu_muc_tam = TemporaryDirectory(prefix="dacn_thu_luu_tru_")
        self.addCleanup(self.thu_muc_tam.cleanup)
        self.thu_muc_goc = Path(self.thu_muc_tam.name)
        self.cau_hinh_tam = override_settings(BASE_DIR=self.thu_muc_goc)
        self.cau_hinh_tam.enable()
        self.addCleanup(self.cau_hinh_tam.disable)

    def test_cau_hinh_project_hien_tai_dat_kiem_tra(self):
        self.assertEqual(kiem_tra_luu_tru(), [])

    def test_bat_buoc_postgresql_cho_tat_ca_ket_noi(self):
        cac_ket_noi = {
            "default": settings.DATABASES["default"],
            "ket_noi_sai": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
        }
        with (
            self.assertWarnsMessage(UserWarning, "Overriding setting DATABASES"),
            override_settings(DATABASES=cac_ket_noi),
        ):
            self.assertIn("luu_tru.E001", {loi.id for loi in kiem_tra_luu_tru()})

    def test_thieu_ket_noi_mac_dinh_bi_chan(self):
        with (
            self.assertWarnsMessage(UserWarning, "Overriding setting DATABASES"),
            override_settings(DATABASES={}),
        ):
            self.assertIn("luu_tru.E001", {loi.id for loi in kiem_tra_luu_tru()})

    def test_session_file_hoac_cache_deu_bi_chan(self):
        for backend in ("file", "cache", "cached_db", "signed_cookies"):
            with (
                self.subTest(backend=backend),
                override_settings(SESSION_ENGINE=f"django.contrib.sessions.backends.{backend}"),
            ):
                self.assertIn("luu_tru.E002", {loi.id for loi in kiem_tra_luu_tru()})

    def test_khai_bao_media_root_ke_ca_rong_cung_bi_chan(self):
        for duong_dan in ("", self.thu_muc_goc / "tai_len"):
            with self.subTest(duong_dan=duong_dan), override_settings(MEDIA_ROOT=duong_dan):
                self.assertIn("luu_tru.E003", {loi.id for loi in kiem_tra_luu_tru()})

    @isolate_apps("ung_dung.chung")
    def test_filefield_va_imagefield_deu_bi_chan_khong_tao_bang(self):
        class MauTepTaiLen(models.Model):
            tep = models.FileField()
            anh = models.ImageField()

            class Meta:
                app_label = "chung"

        cac_loi = kiem_tra_luu_tru(app_configs=MauTepTaiLen._meta.apps.get_app_configs())
        self.assertEqual(sum(loi.id == "luu_tru.E004" for loi in cac_loi), 2)

    def test_moi_duoi_tep_du_lieu_bi_chan_ke_ca_trong_static(self):
        thu_muc = self.thu_muc_goc / "static"
        thu_muc.mkdir()
        for duoi_tep in DUOI_TEP_DU_LIEU:
            (thu_muc / f"mau{duoi_tep.upper()}").touch()
        self.assertEqual(len(tim_tep_du_lieu(self.thu_muc_goc)), len(DUOI_TEP_DU_LIEU))
        self.assertEqual(
            sum(loi.id == "luu_tru.E006" for loi in kiem_tra_luu_tru()), len(DUOI_TEP_DU_LIEU)
        )

    def test_anh_ngoai_static_bi_chan(self):
        for duoi_tep in DUOI_TEP_ANH:
            (self.thu_muc_goc / f"mau{duoi_tep}").touch()
        self.assertEqual(len(tim_tep_du_lieu(self.thu_muc_goc)), len(DUOI_TEP_ANH))

    def test_duoi_gis_backup_mo_hinh_va_file_nen_duoc_bao_ve(self):
        cac_duoi_bat_buoc = {
            ".geojson",
            ".shp",
            ".shx",
            ".dbf",
            ".prj",
            ".gpkg",
            ".kml",
            ".kmz",
            ".sql",
            ".dump",
            ".backup",
            ".npy",
            ".npz",
            ".h5",
            ".hdf5",
            ".pt",
            ".onnx",
            ".zip",
            ".7z",
        }
        self.assertTrue(cac_duoi_bat_buoc <= DUOI_TEP_DU_LIEU)

    def test_khong_cam_giay_phep_txt_va_ma_migration(self):
        thu_muc = self.thu_muc_goc / "static/vendor/font"
        thu_muc.mkdir(parents=True)
        (thu_muc / "OFL.txt").write_text("Giấy phép", encoding="utf-8")
        (self.thu_muc_goc / "0001_tao_bang.py").write_text(
            'SQL = "CREATE TABLE ..."', encoding="utf-8"
        )
        self.assertEqual(tim_tep_du_lieu(self.thu_muc_goc), [])

    def test_anh_tai_static_toan_cuc_va_static_phan_he_duoc_phep(self):
        for ten_thu_muc in ("static/vendor", "ung_dung/webgis/static/webgis"):
            thu_muc = self.thu_muc_goc / ten_thu_muc
            thu_muc.mkdir(parents=True)
            (thu_muc / "ban_do.png").touch()
            (thu_muc / "bieu_tuong.svg").touch()
        self.assertEqual(tim_tep_du_lieu(self.thu_muc_goc), [])

    def test_bo_qua_cac_thu_muc_san_pham_sinh_va_git(self):
        for ten_thu_muc in THU_MUC_BO_QUA:
            thu_muc = self.thu_muc_goc / ten_thu_muc / "long_nhau"
            thu_muc.mkdir(parents=True)
            (thu_muc / "san_pham_sinh.json").touch()
        self.assertEqual(tim_tep_du_lieu(self.thu_muc_goc), [])

    def test_file_log_handler_bi_chan(self):
        with override_settings(
            LOGGING={
                "version": 1,
                "handlers": {
                    "tep": {
                        "class": "logging.FileHandler",
                        "filename": str(self.thu_muc_goc / "cam.log"),
                    }
                },
            }
        ):
            self.assertIn("luu_tru.E007", {loi.id for loi in kiem_tra_luu_tru()})

    def test_base_dir_khong_ton_tai_bi_chan(self):
        with override_settings(BASE_DIR=self.thu_muc_goc / "khong_ton_tai"):
            self.assertIn("luu_tru.E005", {loi.id for loi in kiem_tra_luu_tru()})

    def test_lenh_quan_ly_tra_ket_qua_dat(self):
        ket_qua = StringIO()
        call_command("kiem_tra_luu_tru", stdout=ket_qua)
        self.assertIn("Đạt", ket_qua.getvalue())

    def test_lenh_quan_ly_tra_loi_khi_co_tep_du_lieu(self):
        (self.thu_muc_goc / "cam.csv").touch()
        with self.assertRaises(CommandError):
            call_command("kiem_tra_luu_tru", stdout=StringIO())
