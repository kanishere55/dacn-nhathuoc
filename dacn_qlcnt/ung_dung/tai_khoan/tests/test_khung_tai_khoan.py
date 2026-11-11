from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from ung_dung.chung.van_ban import MA_KHOANG_TRANG


class KhungTaiKhoanTests(TestCase):
    def test_tao_va_xac_thuc_bang_co_che_django(self):
        tai_khoan = get_user_model().objects.create_user(
            "nguoi_thu", password="Mat-khau-chi-dung-trong-test!"
        )
        self.assertNotEqual(tai_khoan.password, "Mat-khau-chi-dung-trong-test!")
        self.assertTrue(tai_khoan.check_password("Mat-khau-chi-dung-trong-test!"))
        self.assertEqual(
            authenticate(ten_dang_nhap="nguoi_thu", password="Mat-khau-chi-dung-trong-test!"),
            tai_khoan,
        )
        self.assertIsNone(authenticate(ten_dang_nhap="nguoi_thu", password="mat-khau-sai"))
        self.assertTrue(tai_khoan.is_active)
        self.assertFalse(tai_khoan.is_staff)
        self.assertFalse(tai_khoan.is_superuser)
        self.assertFalse(tai_khoan.has_perm("kho.xac_nhan_phieu_nhap"))

    def test_dang_nhap_luu_session_va_thoi_diem_trong_csdl(self):
        get_user_model().objects.create_user(
            "dang_nhap_thu", password="Mat-khau-chi-dung-trong-test!"
        )
        self.assertTrue(
            self.client.login(
                ten_dang_nhap="dang_nhap_thu",
                password="Mat-khau-chi-dung-trong-test!",
            )
        )
        tai_khoan = get_user_model().objects.get(ten_dang_nhap="dang_nhap_thu")
        self.assertIsNotNone(tai_khoan.last_login)
        from django.contrib.sessions.models import Session

        self.assertTrue(
            Session.objects.filter(session_key=self.client.session.session_key).exists()
        )

    def test_nhap_sai_5_lan_tam_khoa_dang_nhap(self):
        from django.urls import reverse

        get_user_model().objects.create_user("khoa_thu", password="Mat-khau-chi-dung-trong-test!")
        url = reverse("tai_khoan:dang_nhap")
        for _ in range(4):
            phan_hoi = self.client.post(url, {"username": "khoa_thu", "password": "sai"})
            self.assertContains(phan_hoi, "không đúng")
        self.assertContains(
            self.client.post(url, {"username": "khoa_thu", "password": "sai"}), "tạm khóa"
        )
        # Đang khóa thì mật khẩu đúng cũng không đăng nhập được.
        phan_hoi = self.client.post(
            url, {"username": "khoa_thu", "password": "Mat-khau-chi-dung-trong-test!"}
        )
        self.assertContains(phan_hoi, "tạm khóa")
        self.assertNotIn("_auth_user_id", self.client.session)
        tai_khoan = get_user_model().objects.get(ten_dang_nhap="khoa_thu")
        tai_khoan.thoi_diem_mo_khoa_dang_nhap = None
        tai_khoan.save(update_fields=["thoi_diem_mo_khoa_dang_nhap"])
        self.client.post(url, {"username": "khoa_thu", "password": "Mat-khau-chi-dung-trong-test!"})
        self.assertIn("_auth_user_id", self.client.session)

    def test_nhan_su_dang_nhap_quay_lai_trang_quan_ly_dang_mo(self):
        get_user_model().objects.create_superuser("qt_quay_lai", password="Mat-khau-thu-2026!")
        url = "/tai-khoan/dang-nhap/?next=/quan-ly/ban-hang/don-hang/%3Ftrang_thai%3Dhoan_thanh"
        du_lieu = {"username": "qt_quay_lai", "password": "Mat-khau-thu-2026!"}
        phan_hoi = self.client.post(url, du_lieu)
        self.assertRedirects(
            phan_hoi,
            "/quan-ly/ban-hang/don-hang/?trang_thai=hoan_thanh",
            fetch_redirect_response=False,
        )
        # Trang khách hoặc trang ngoài: nhân sự vẫn về bảng điều khiển.
        self.client.logout()
        phan_hoi = self.client.post("/tai-khoan/dang-nhap/?next=https://vi-du.com/", du_lieu)
        self.assertRedirects(phan_hoi, "/quan-ly/", fetch_redirect_response=False)

    def test_khach_dang_nhap_voi_next_khu_quan_ly_ve_trang_chu(self):
        get_user_model().objects.create_user("khach_next", password="Mat-khau-thu-2026!")
        du_lieu = {"username": "khach_next", "password": "Mat-khau-thu-2026!"}
        phan_hoi = self.client.post("/tai-khoan/dang-nhap/?next=/quan-ly/", du_lieu)
        self.assertRedirects(phan_hoi, "/", fetch_redirect_response=False)
        self.client.logout()
        phan_hoi = self.client.post("/tai-khoan/dang-nhap/?next=/gio-hang/", du_lieu)
        self.assertRedirects(phan_hoi, "/gio-hang/", fetch_redirect_response=False)

    def test_khong_xac_thuc_tai_khoan_ngung_hoat_dong(self):
        get_user_model().objects.create_user(
            "ngung_hoat_dong", password="Mat-khau-thu!", dang_hoat_dong=False
        )
        self.assertIsNone(authenticate(ten_dang_nhap="ngung_hoat_dong", password="Mat-khau-thu!"))

    def test_tao_quan_tri_he_thong_co_vai_tro_quan_tri_chuoi(self):
        tai_khoan = get_user_model().objects.create_superuser(
            "quan_tri_thu", password="Mat-khau-thu!"
        )
        self.assertTrue(tai_khoan.is_superuser)
        self.assertTrue(tai_khoan.is_staff)
        self.assertEqual(tai_khoan.vai_tro, "quan_tri_chuoi")
        self.assertTrue(tai_khoan.has_perm("quyen_thu_nghiem"))
        self.assertEqual(list(tai_khoan._meta.many_to_many), [])
        with self.assertRaises(ValueError):
            get_user_model().objects.create_superuser(
                "quan_tri_sai", password="Mat-khau-thu!", la_quan_tri_he_thong=False
            )
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user(
                "tu_nang_quyen", password="Mat-khau-thu!", la_quan_tri_he_thong=True
            )
        with self.assertRaises(IntegrityError) as loi, transaction.atomic():
            get_user_model().objects.filter(pk=tai_khoan.pk).update(vai_tro="khach_hang")
        self.assertEqual(loi.exception.__cause__.sqlstate, "23514")
        self.assertEqual(
            loi.exception.__cause__.diag.constraint_name,
            "kiem_tra__tai_khoan__quan_tri_he_thong_dung_vai_tro",
        )

    def test_cat_dung_toan_bo_khoang_trang_truoc_khi_luu(self):
        khoang_trang = "".join(chr(ma) for ma in MA_KHOANG_TRANG)
        tai_khoan = get_user_model().objects.create_user(
            khoang_trang + "Tên_đăng_nhập_thử" + khoang_trang
        )
        self.assertEqual(tai_khoan.ten_dang_nhap, "Tên_đăng_nhập_thử")
        self.assertFalse(tai_khoan.has_usable_password())

    def test_khong_tao_ten_rong(self):
        for ten in (None, "", " \t\n", "\u200b\ufeff"):
            with self.subTest(ten=repr(ten)), self.assertRaises(ValueError):
                get_user_model().objects.create_user(ten)

    def test_db_chan_ten_trung_voi_dung_ten_rang_buoc(self):
        get_user_model().objects.create_user("ten_trung")
        with self.assertRaises(IntegrityError) as loi:
            with transaction.atomic():
                get_user_model().objects.create_user("ten_trung")
        self.assertEqual(loi.exception.__cause__.sqlstate, "23505")
        self.assertEqual(
            loi.exception.__cause__.diag.constraint_name,
            "duy_nhat__tai_khoan__ten_dang_nhap",
        )

    def test_db_chan_ghi_thang_ten_sai(self):
        cac_ca = (
            ("", {"kiem_tra__tai_khoan__ten_dang_nhap_khong_rong"}),
            (
                "\u3000ten_thu",
                {"kiem_tra__tai_khoan__ten_dang_nhap_da_cat_khoang_trang"},
            ),
            ("ten\u2028thu", {"kiem_tra__tai_khoan__ten_dang_nhap_mot_dong"}),
            ("ten\u2029thu", {"kiem_tra__tai_khoan__ten_dang_nhap_mot_dong"}),
        )
        for ten, rang_buoc in cac_ca:
            with self.subTest(ten=repr(ten)):
                with self.assertRaises(IntegrityError) as loi:
                    with transaction.atomic():
                        get_user_model().objects.create(
                            ten_dang_nhap=ten, password="!chuoi-khong-dang-nhap-duoc"
                        )
                self.assertEqual(loi.exception.__cause__.sqlstate, "23514")
                self.assertIn(loi.exception.__cause__.diag.constraint_name, rang_buoc)

    def test_db_chan_chuoi_bam_sai(self):
        cac_ca = (
            ("", "kiem_tra__tai_khoan__mat_khau_bam_khong_rong"),
            ("\ufeffchuoi_bam", "kiem_tra__tai_khoan__mat_khau_bam_da_cat_khoang_trang"),
            ("chuoi\n_bam", "kiem_tra__tai_khoan__mat_khau_bam_mot_dong"),
        )
        for chuoi_bam, rang_buoc in cac_ca:
            with self.subTest(chuoi_bam=repr(chuoi_bam)):
                with self.assertRaises(IntegrityError) as loi:
                    with transaction.atomic():
                        get_user_model().objects.create(
                            ten_dang_nhap="kiem_tra_chuoi_bam", password=chuoi_bam
                        )
                self.assertEqual(loi.exception.__cause__.sqlstate, "23514")
                self.assertEqual(loi.exception.__cause__.diag.constraint_name, rang_buoc)

    def test_schema_tai_khoan_va_day_du_chu_thich(self):
        self.assertEqual(connection.vendor, "postgresql")
        with connection.cursor() as con_tro:
            con_tro.execute(
                """
                SELECT a.attname, col_description(a.attrelid, a.attnum)
                FROM pg_attribute a
                WHERE a.attrelid = 'tai_khoan'::regclass
                    AND a.attnum > 0 AND NOT a.attisdropped
                ORDER BY a.attnum
                """
            )
            cac_cot = con_tro.fetchall()
            self.assertEqual(
                [cot[0] for cot in cac_cot],
                [
                    "id_tai_khoan",
                    "ten_dang_nhap",
                    "mat_khau_bam",
                    "dang_hoat_dong",
                    "la_quan_tri_he_thong",
                    "thoi_diem_dang_nhap_cuoi",
                    "id_chi_nhanh",
                    "vai_tro",
                    "da_xac_thuc_email",
                    "email",
                    "ho_ten",
                    "so_dien_thoai",
                    "thoi_diem_tao",
                    "id_dia_chi_giao_hang_mac_dinh",
                    "id_nhom_quyen",
                    "so_lan_dang_nhap_sai",
                    "thoi_diem_mo_khoa_dang_nhap",
                ],
            )
            self.assertTrue(all(cot[1] for cot in cac_cot))
            con_tro.execute("SELECT obj_description('tai_khoan'::regclass, 'pg_class')")
            self.assertTrue(con_tro.fetchone()[0])
            con_tro.execute(
                """
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'tai_khoan'::regclass
                AND contype IN ('p', 'u', 'c')
                """
            )
            cac_ten = {hang[0] for hang in con_tro.fetchall()}
            self.assertIn("khoa_chinh__tai_khoan", cac_ten)
            self.assertTrue(all(len(ten.encode()) <= 63 for ten in cac_ten))
            con_tro.execute(
                """
                SELECT obj_description(oid, 'pg_constraint')
                FROM pg_constraint
                WHERE conrelid = 'tai_khoan'::regclass AND contype = 'c'
                """
            )
            self.assertTrue(all(hang[0] for hang in con_tro.fetchall()))

    def test_boolean_co_mac_dinh_ngay_tai_db(self):
        with connection.cursor() as con_tro:
            con_tro.execute(
                """
                INSERT INTO tai_khoan (ten_dang_nhap, mat_khau_bam)
                VALUES (%s, %s)
                RETURNING dang_hoat_dong, la_quan_tri_he_thong
                """,
                ["mac_dinh_db", "!khong-dang-nhap-duoc"],
            )
            self.assertEqual(con_tro.fetchone(), (True, False))
