"""Các lỗi do review độc lập phát hiện: phạm vi chi nhánh, thao tác ảnh, quyền riêng, bộ lọc."""

from io import StringIO

from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ung_dung.ban_hang.services.dat_hang import dat_giu
from ung_dung.danh_muc.forms import TaiAnhForm
from ung_dung.kho.services.lo_thuoc import doi_dieu_kien_ban
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton
from ung_dung.tai_khoan.models import QuyenRiengTaiKhoan

from ..models import AnhChiNhanh, DanhGiaChiNhanh
from ..services.anh import them_anh, xoa_anh
from .test_anh_va_khuyen_mai import tep_anh

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def cap_quyen(nguoi, *ma_quyen):
    for ma in ma_quyen:
        QuyenRiengTaiKhoan.objects.create(tai_khoan=nguoi, ma_quyen=ma, duoc_phep=True)


class PhamViChiNhanhTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        cap_quyen(cls.d.nv, "chi_nhanh.sua", "chi_nhanh.xem", "lo_thuoc.sua", "lo_thuoc.xem")
        cls.anh_cn2 = them_anh(cls.d.admin, "chi_nhanh", cls.d.cn2, [tep_anh()])[0]
        cls.anh_cn1 = them_anh(cls.d.admin, "chi_nhanh", cls.d.cn, [tep_anh()])[0]

    def setUp(self):
        self.client.force_login(self.d.nv)

    def test_khong_xoa_anh_chi_nhanh_khac_qua_post_hay_service(self):
        url = reverse("danh_muc:anh_xoa", args=["chi_nhanh", self.d.cn2.pk, self.anh_cn2.pk])
        self.assertEqual(self.client.post(url, **AJAX).status_code, 404)
        with self.assertRaises(PermissionDenied):
            xoa_anh(self.d.nv, "chi_nhanh", self.d.cn2, self.anh_cn2.pk)
        with self.assertRaises(PermissionDenied):
            them_anh(self.d.nv, "chi_nhanh", self.d.cn2, [tep_anh()])
        self.assertTrue(AnhChiNhanh.objects.filter(pk=self.anh_cn2.pk).exists())

    def test_sua_duoc_anh_chi_nhanh_cua_minh(self):
        url = reverse("danh_muc:anh_xoa", args=["chi_nhanh", self.d.cn.pk, self.anh_cn1.pk])
        self.assertEqual(self.client.post(url, **AJAX).status_code, 200)
        self.assertFalse(AnhChiNhanh.objects.filter(pk=self.anh_cn1.pk).exists())

    def test_nhan_vien_khong_tao_chi_nhanh_moi(self):
        trang = self.client.post(
            reverse("danh_muc:chi_nhanh_tao"),
            {
                "ma_chi_nhanh": "CN8",
                "ten_chi_nhanh": "Trái phép",
                "dia_chi": "TP.HCM",
                "dang_hoat_dong": "on",
                "gio_mo_cua": "07:00",
                "gio_dong_cua": "22:00",
                "kinh_do": "106.7",
                "vi_do": "10.7",
            },
        )
        self.assertEqual(trang.status_code, 403)
        self.assertFalse(
            type(self.d.cn).objects.filter(ma_chi_nhanh="CN8").exists(),
        )

    def test_doi_dieu_kien_ban_cua_lo_can_pham_vi_toan_chuoi(self):
        ton = tao_ton(self.d, "LO-RV", chi_nhanh=self.d.cn2, luong=5)
        with self.assertRaises(PermissionDenied):
            doi_dieu_kien_ban(self.d.nv, ton.lo_thuoc, False)
        url = reverse("kho:lo_thuoc_doi_trang_thai", args=[ton.lo_thuoc.pk])
        self.assertEqual(self.client.post(url, {"duoc_phep_ban": "0"}).status_code, 403)
        ton.lo_thuoc.refresh_from_db()
        self.assertTrue(ton.lo_thuoc.duoc_phep_ban)
        cap_quyen(self.d.nv, "pham_vi.toan_chuoi")
        self.client.force_login(self.d.nv)
        self.assertEqual(self.client.post(url, {"duoc_phep_ban": "0"}).status_code, 302)

    def test_tong_quan_khong_lo_don_va_nut_khi_thieu_quyen(self):
        tao_ton(self.d, luong=20)
        don = dat_giu(self.d.khach, self.d.cn, [{"thuoc": self.d.thuoc, "so_luong": 1}])
        # nhân viên mặc định có quyền xem đơn và bán
        trang = self.client.get(reverse("chung:bang_dieu_khien"))
        self.assertContains(trang, don.ma_don_hang)
        QuyenRiengTaiKhoan.objects.create(
            tai_khoan=self.d.nv, ma_quyen="don_hang.xem", duoc_phep=False
        )
        QuyenRiengTaiKhoan.objects.create(
            tai_khoan=self.d.nv, ma_quyen="phieu_ban.tao", duoc_phep=False
        )
        self.client.force_login(self.d.nv)
        trang = self.client.get(reverse("chung:bang_dieu_khien"))
        self.assertNotContains(trang, don.ma_don_hang)
        self.assertNotContains(trang, reverse("ban_hang:phieu_ban_tao"))

    def test_ban_do_nhiet_chi_tra_chi_nhanh_trong_pham_vi(self):
        cap_quyen(self.d.nv, "ban_do_nhiet.xem")
        tao_ton(self.d, luong=10)
        tao_ton(self.d, "LO-HAI", chi_nhanh=self.d.cn2, luong=10)
        self.client.force_login(self.d.nv)
        phan_hoi = self.client.get(
            reverse("webgis:du_lieu_nhiet"),
            {"nhom_atc": self.d.nhom.pk, "don_vi_tinh": self.d.dvt.pk},
        )
        self.assertEqual(phan_hoi.status_code, 200)
        ten = [dong["ten_chi_nhanh"] for dong in phan_hoi.json()["ket_qua"]]
        self.assertEqual(ten, [self.d.cn.ten_chi_nhanh])

    def test_kiem_duyet_danh_gia_chi_nhanh_trong_pham_vi(self):
        cap_quyen(self.d.nv, "danh_gia.xem", "danh_gia.kiem_duyet")
        dg2 = DanhGiaChiNhanh.objects.create(
            chi_nhanh=self.d.cn2, khach_hang=self.d.khach, so_sao=5, thoi_diem_tao=timezone.now()
        )
        self.client.force_login(self.d.nv)
        trang = self.client.get(reverse("danh_muc:danh_gia_danh_sach"), {"loai": "chi_nhanh"})
        self.assertEqual(trang.context["trang"].paginator.count, 0)
        url = reverse("danh_muc:danh_gia_chi_nhanh_doi_hien_thi", args=[dg2.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        dg2.refresh_from_db()
        self.assertTrue(dg2.dang_hien_thi)


class ThaoTacAnhVaLocTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def setUp(self):
        self.client.force_login(self.d.admin)

    def test_o_chon_tep_khong_dat_required_de_js_gui_duoc(self):
        self.assertNotIn("required", str(TaiAnhForm()["cac_anh"]))
        trang = self.client.get(reverse("danh_muc:thuoc_sua", args=[self.d.thuoc.pk]))
        self.assertContains(trang, "data-form-tai-anh novalidate")

    def test_xoa_va_dat_dai_dien_nhan_body_urlencoded_rong(self):
        cac_anh = them_anh(self.d.admin, "thuoc", self.d.thuoc, [tep_anh(), tep_anh()])
        url = reverse("danh_muc:anh_dai_dien", args=["thuoc", self.d.thuoc.pk, cac_anh[1].pk])
        phan_hoi = self.client.post(
            url, "", content_type="application/x-www-form-urlencoded", **AJAX
        )
        self.assertEqual(phan_hoi.status_code, 200)
        self.assertEqual(phan_hoi.json()["cac_anh"][0]["id"], cac_anh[1].pk)

    def test_so_dong_qua_dai_khong_gay_500(self):
        phan_hoi = self.client.get(reverse("danh_muc:thuoc_danh_sach"), {"moi_trang": "9" * 5000})
        self.assertEqual(phan_hoi.status_code, 200)
        self.assertEqual(phan_hoi.context["loc"].moi_trang, 25)

    def test_chuyen_vai_tro_bo_nhom_quyen_cu_va_luu_duoc(self):
        from ung_dung.tai_khoan.services.quyen import luu_nhom_quyen

        nhom = luu_nhom_quyen(
            self.d.admin,
            {"ma_nhom_quyen": "NHOM-TAM", "ten_nhom_quyen": "Nhóm tạm", "mo_ta": ""},
            ["ton_kho.xem"],
        )
        self.d.nv.nhom_quyen = nhom
        self.d.nv.save()
        phan_hoi = self.client.post(
            reverse("tai_khoan:sua", args=[self.d.nv.pk]),
            {
                "ten_dang_nhap": self.d.nv.ten_dang_nhap,
                "vai_tro": "khach_hang",
                "chi_nhanh": "",
                "dang_hoat_dong": "on",
                "nhom_quyen": str(nhom.pk),  # giá trị cũ vẫn bị gửi lên
            },
        )
        self.assertEqual(phan_hoi.status_code, 302)
        self.d.nv.refresh_from_db()
        self.assertEqual((self.d.nv.vai_tro, self.d.nv.nhom_quyen_id), ("khach_hang", None))

    def test_bang_quyen_rieng_co_css_khong_float_legend(self):
        import pathlib

        css = pathlib.Path("static/css/quan_ly.css").read_text(encoding="utf-8")
        self.assertIn(".nhom-form .ma-tran-quyen legend", css)

    def test_nap_anh_that_khong_ghi_de_anh_tai_thu_cong(self):
        from ..management.commands.nap_anh_that import Command
        from ..models import AnhThuoc

        them_anh(self.d.admin, "thuoc", self.d.thuoc, [tep_anh()])
        muc = {"tac_gia": "A", "giay_phep": "CC0", "trang": "https://commons.example/File:X.jpg"}
        lenh = Command(stdout=StringIO())
        du_lieu = tep_anh().read()
        self.assertFalse(lenh._them(AnhThuoc, self.d.thuoc, "thuoc", muc, du_lieu, 0, ""))
        self.assertEqual(AnhThuoc.objects.filter(thuoc=self.d.thuoc).count(), 1)
        self.assertEqual(AnhThuoc.objects.get(thuoc=self.d.thuoc).nguon_anh, "")
        call_command("check", stdout=StringIO())
        self.assertIsInstance(SimpleUploadedFile("a", b"x"), SimpleUploadedFile)

    def test_htmx_tra_nut_xoa_loc_va_tong_so_de_cap_nhat(self):
        trang = self.client.get(reverse("danh_muc:thuoc_danh_sach"), {"tim": "x"})
        self.assertContains(trang, 'id="nut-xoa-loc"')
        self.assertContains(trang, "Xóa lọc")
        self.assertContains(trang, 'hx-select-oob="#nut-xoa-loc,#tong-so-ban-ghi"')
        self.assertContains(trang, 'id="tong-so-ban-ghi"')
