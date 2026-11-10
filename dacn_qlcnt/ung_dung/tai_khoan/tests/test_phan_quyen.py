from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from ung_dung.chung.permissions import co_quyen, kiem_tra_quyen_ghi_chi_nhanh, thay_toan_chuoi
from ung_dung.kho.tests.du_lieu import tao_du_lieu

from .. import quyen as danh_muc_quyen
from ..models import NhomQuyen, QuyenCuaNhom, QuyenRiengTaiKhoan
from ..services.quyen import (
    bao_dam_nhom_mac_dinh,
    luu_nhom_quyen,
    luu_quyen_rieng,
    tinh_quyen_hieu_luc,
    xoa_nhom_quyen,
)
from ..services.tai_khoan import luu_tai_khoan


def moi(nguoi):
    """Lấy lại từ CSDL để bỏ bộ nhớ đệm quyền trên đối tượng người dùng."""
    return type(nguoi).objects.get(pk=nguoi.pk)


class QuyenHieuLucTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_quan_tri_co_moi_quyen_va_khach_khong_co_quyen_nao(self):
        self.assertEqual(tinh_quyen_hieu_luc(self.d.admin), danh_muc_quyen.MA_QUYEN)
        self.assertTrue(thay_toan_chuoi(self.d.admin))
        self.assertEqual(tinh_quyen_hieu_luc(self.d.khach), frozenset())

    def test_quyen_mac_dinh_cua_vai_tro_khi_chua_gan_nhom(self):
        self.assertIn("phieu_nhap.tao", tinh_quyen_hieu_luc(self.d.nv))
        self.assertNotIn("dieu_chuyen.tao", tinh_quyen_hieu_luc(self.d.nv))
        self.assertIn("dieu_chuyen.tao", tinh_quyen_hieu_luc(self.d.ql))
        self.assertNotIn("thuoc.sua", tinh_quyen_hieu_luc(self.d.ql))
        self.assertFalse(thay_toan_chuoi(self.d.ql))

    def test_nhom_tuy_chinh_va_quyen_rieng_cho_them_hoac_chan(self):
        d = self.d
        nhom = luu_nhom_quyen(
            d.admin,
            {"ma_nhom_quyen": "DUOC-SI-KHO", "ten_nhom_quyen": "Dược sĩ kho", "mo_ta": ""},
            ["ton_kho.xem", "phieu_nhap.xem", "phieu_nhap.tao", "thuoc.sua"],
        )
        luu_tai_khoan(
            d.admin,
            {
                "ten_dang_nhap": d.nv.ten_dang_nhap,
                "vai_tro": "nhan_vien",
                "chi_nhanh": d.cn,
                "dang_hoat_dong": True,
                "nhom_quyen": nhom,
            },
            d.nv,
        )
        nv = moi(d.nv)
        self.assertEqual(
            tinh_quyen_hieu_luc(nv),
            frozenset({"ton_kho.xem", "phieu_nhap.xem", "phieu_nhap.tao", "thuoc.sua"}),
        )
        luu_quyen_rieng(d.admin, nv, {"phieu_nhap.tao": False, "kiem_ke.tao": True})
        quyen = tinh_quyen_hieu_luc(moi(nv))
        self.assertNotIn("phieu_nhap.tao", quyen)
        self.assertIn("kiem_ke.tao", quyen)
        self.assertIn("thuoc.sua", quyen)

    def test_khong_giao_duoc_quyen_chi_danh_cho_quan_tri(self):
        with self.assertRaises(ValidationError):
            luu_nhom_quyen(
                self.d.admin,
                {"ma_nhom_quyen": "NHOM-X", "ten_nhom_quyen": "Nhóm X", "mo_ta": ""},
                ["tai_khoan.sua"],
            )
        with self.assertRaises(ValidationError):
            luu_quyen_rieng(self.d.admin, self.d.nv, {"phan_quyen.quan_ly": True})

    def test_chi_quan_tri_duoc_quan_ly_phan_quyen(self):
        with self.assertRaises(PermissionDenied):
            luu_nhom_quyen(
                self.d.ql,
                {"ma_nhom_quyen": "NHOM-Y", "ten_nhom_quyen": "Nhóm Y", "mo_ta": ""},
                [],
            )
        self.client.force_login(self.d.ql)
        self.assertEqual(
            self.client.get(reverse("tai_khoan:nhom_quyen_danh_sach")).status_code, 403
        )
        self.assertEqual(self.client.get(reverse("tai_khoan:tao")).status_code, 403)

    def test_nhom_mac_dinh_sua_duoc_nhung_khong_xoa_duoc(self):
        bao_dam_nhom_mac_dinh()
        nhom = NhomQuyen.objects.get(vai_tro_mac_dinh="nhan_vien")
        self.assertEqual(
            set(nhom.cac_quyen.values_list("ma_quyen", flat=True)),
            set(danh_muc_quyen.MAC_DINH["nhan_vien"]),
        )
        with self.assertRaises(ValidationError):
            xoa_nhom_quyen(self.d.admin, nhom)
        QuyenCuaNhom.objects.filter(nhom_quyen=nhom, ma_quyen="phieu_ban.tao").delete()
        self.assertNotIn("phieu_ban.tao", tinh_quyen_hieu_luc(moi(self.d.nv)))
        self.assertIn("phieu_ban.tao", tinh_quyen_hieu_luc(moi(self.d.ql)))

    def test_nhom_dang_dung_khong_xoa_duoc(self):
        d = self.d
        nhom = luu_nhom_quyen(
            d.admin, {"ma_nhom_quyen": "TAM", "ten_nhom_quyen": "Tạm", "mo_ta": ""}, ["ton_kho.xem"]
        )
        luu_tai_khoan(
            d.admin,
            {
                "ten_dang_nhap": d.nv.ten_dang_nhap,
                "vai_tro": "nhan_vien",
                "chi_nhanh": d.cn,
                "dang_hoat_dong": True,
                "nhom_quyen": nhom,
            },
            d.nv,
        )
        with self.assertRaises(ValidationError):
            xoa_nhom_quyen(d.admin, nhom)

    def test_doi_sang_quan_tri_xoa_nhom_va_quyen_rieng(self):
        d = self.d
        QuyenRiengTaiKhoan.objects.create(tai_khoan=d.nv, ma_quyen="kiem_ke.tao", duoc_phep=True)
        luu_tai_khoan(
            d.admin,
            {
                "ten_dang_nhap": d.nv.ten_dang_nhap,
                "vai_tro": "quan_tri_chuoi",
                "chi_nhanh": None,
                "dang_hoat_dong": True,
                "quyen_rieng": {"kiem_ke.tao": True},
            },
            d.nv,
        )
        self.assertFalse(QuyenRiengTaiKhoan.objects.filter(tai_khoan=d.nv).exists())

    def test_quyen_ghi_theo_chi_nhanh_va_pham_vi_toan_chuoi(self):
        d = self.d
        kiem_tra_quyen_ghi_chi_nhanh(d.nv, d.cn, "phieu_nhap.tao")
        with self.assertRaises(PermissionDenied):
            kiem_tra_quyen_ghi_chi_nhanh(d.nv, d.cn2, "phieu_nhap.tao")
        kiem_tra_quyen_ghi_chi_nhanh(d.admin, d.cn2, "phieu_nhap.tao")
        QuyenRiengTaiKhoan.objects.create(
            tai_khoan=d.nv, ma_quyen="pham_vi.toan_chuoi", duoc_phep=True
        )
        kiem_tra_quyen_ghi_chi_nhanh(moi(d.nv), d.cn2, "phieu_nhap.tao")
        self.assertTrue(co_quyen(moi(d.nv), "pham_vi.toan_chuoi"))


class GiaoDienPhanQuyenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def setUp(self):
        self.client.force_login(self.d.admin)

    def test_tao_nhom_quyen_qua_trang_va_gan_cho_tai_khoan(self):
        phan_hoi = self.client.post(
            reverse("tai_khoan:nhom_quyen_tao"),
            {
                "ma_nhom_quyen": "KIEM-KE-VIEN",
                "ten_nhom_quyen": "Kiểm kê viên",
                "cac_quyen": ["ton_kho.xem", "kiem_ke.xem", "kiem_ke.tao"],
            },
        )
        self.assertEqual(phan_hoi.status_code, 302)
        nhom = NhomQuyen.objects.get(ma_nhom_quyen="KIEM-KE-VIEN")
        self.assertEqual(nhom.cac_quyen.count(), 3)
        trang = self.client.get(reverse("tai_khoan:sua", args=[self.d.nv.pk]))
        self.assertContains(trang, "Kiểm kê viên")
        self.assertContains(trang, "Chọn nhanh theo nhóm quyền")

    def test_menu_chi_hien_muc_duoc_phep(self):
        self.client.force_login(self.d.nv)
        trang = self.client.get(reverse("chung:bang_dieu_khien"))
        self.assertContains(trang, reverse("kho:phieu_nhap_danh_sach"))
        self.assertNotContains(trang, reverse("kho:phieu_dieu_chuyen_danh_sach"))
        self.assertNotContains(trang, reverse("tai_khoan:nhom_quyen_danh_sach"))
        QuyenRiengTaiKhoan.objects.create(
            tai_khoan=self.d.nv, ma_quyen="dieu_chuyen.xem", duoc_phep=True
        )
        self.client.force_login(self.d.nv)
        trang = self.client.get(reverse("chung:bang_dieu_khien"))
        self.assertContains(trang, reverse("kho:phieu_dieu_chuyen_danh_sach"))

    def test_danh_sach_tai_khoan_loc_va_phan_trang(self):
        trang = self.client.get(reverse("tai_khoan:danh_sach"), {"vai_tro": "nhan_vien"})
        self.assertContains(trang, self.d.nv.ten_dang_nhap)
        self.assertNotContains(trang, self.d.ql.ten_dang_nhap)
        trang = self.client.get(reverse("tai_khoan:danh_sach"), {"tim": "khach_khac"})
        self.assertContains(trang, "khach_khac")
        self.assertEqual(trang.context["trang"].paginator.count, 1)


class TickQuyenTungNguoiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def test_tick_them_va_bo_bot_luu_thanh_quyen_rieng(self):
        from .. import quyen as dm

        self.client.force_login(self.d.admin)
        nv = self.d.nv
        du_lieu = {
            "ten_dang_nhap": nv.ten_dang_nhap,
            "vai_tro": "nhan_vien",
            "chi_nhanh": nv.chi_nhanh_id,
            "dang_hoat_dong": "on",
        }
        co_so = set(dm.MAC_DINH["nhan_vien"]) - {"phieu_nhap.tao"}
        for ma in co_so | {"du_bao.xem"}:
            du_lieu["quyen__" + ma.replace(".", "__")] = "on"
        phan_hoi = self.client.post(reverse("tai_khoan:sua", args=[nv.pk]), du_lieu)
        self.assertEqual(phan_hoi.status_code, 302)
        rieng = dict(
            QuyenRiengTaiKhoan.objects.filter(tai_khoan=nv).values_list("ma_quyen", "duoc_phep")
        )
        self.assertEqual(rieng, {"du_bao.xem": True, "phieu_nhap.tao": False})
        quyen = tinh_quyen_hieu_luc(moi(nv))
        self.assertIn("du_bao.xem", quyen)
        self.assertNotIn("phieu_nhap.tao", quyen)
        trang = self.client.get(reverse("tai_khoan:sua", args=[nv.pk]))
        self.assertRegex(trang.content.decode(), r'data-ma-quyen="du_bao\.xem"[^>]*checked')
        self.assertNotRegex(trang.content.decode(), r'data-ma-quyen="phieu_nhap\.tao"[^>]*checked')
