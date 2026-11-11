from datetime import timedelta
from io import BytesIO
from unittest import mock

from django.contrib.gis.geos import Point
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton
from ung_dung.thanh_toan.models import GiaoDichThanhToan
from ung_dung.thanh_toan.services.cong import da_thu_tien_cod
from ung_dung.thong_bao.models import NhatKyEmail

from ..models import LichSuDonHang, YeuCauTraHang
from ..services.dat_hang import dat_hang
from ..services.don_hang import giao_cho_van_chuyen, xac_nhan_da_giao, xac_nhan_don
from ..services.tra_hang import duyet, hoan_tien_tra_hang, tao_yeu_cau, tu_choi


def anh_thu(ten="hop.png"):
    dem = BytesIO()
    Image.new("RGB", (40, 30), (200, 80, 80)).save(dem, "PNG")
    return SimpleUploadedFile(ten, dem.getvalue(), content_type="image/png")


class TraHangTests(TestCase):
    def setUp(self):
        self.d = tao_du_lieu()
        self.d.khach.email = "khach@example.com"
        self.d.khach.save()
        tao_ton(self.d, ngay=60, luong=20)
        with mock.patch("ung_dung.ban_hang.services.thong_bao_don.tep_hoa_don", return_value=None):
            self.don = dat_hang(
                self.d.khach,
                self.d.cn,
                [{"thuoc": self.d.thuoc, "so_luong": 4}],
                hinh_thuc_nhan="giao_hang",
                phuong_thuc_thanh_toan="cod",
                giao={
                    "ten_nguoi_nhan": "Khách",
                    "so_dien_thoai": "0901234567",
                    "dia_chi": "1 Lê Lợi",
                    "vi_tri": Point(106.70, 10.77, srid=4326),
                    "khoang_cach_met": 1000,
                },
            )
            xac_nhan_don(self.d.nv, self.don)
            giao_cho_van_chuyen(self.d.nv, self.don)
            xac_nhan_da_giao(self.d.khach, self.don)
        da_thu_tien_cod(self.d.ql, self.don)
        self.dong = self.don.cac_dong.get()

    def tao(self, so_luong=2, cac_anh=None):
        return tao_yeu_cau(
            self.d.khach,
            self.don,
            ly_do="hu_hong",
            mo_ta="Hộp bị móp, vỉ rách",
            cac_dong={self.dong.pk: so_luong},
            cac_anh=[anh_thu()] if cac_anh is None else cac_anh,
        )

    def test_quy_trinh_duyet_va_hoan_tien(self):
        yc = self.tao()
        self.assertEqual((yc.trang_thai, yc.so_tien_hoan), ("cho_duyet", 4000))
        self.assertRegex(yc.ma_yeu_cau_tra_hang, r"^TH\d{6}[2-9A-HJKMNP-Z]{5}$")
        with self.assertRaises(ValidationError):
            self.tao()  # đang có yêu cầu chưa xử lý
        with self.assertRaises(PermissionDenied):
            duyet(self.d.nv, yc)
        with self.assertRaises(PermissionDenied):
            duyet(self.d.ql2, yc)
        duyet(self.d.ql, yc, "Đã nhận lại hộp móp")
        hoan_tien_tra_hang(self.d.ql, yc, phuong_thuc="tien_mat")
        yc.refresh_from_db()
        self.assertEqual(yc.trang_thai, "da_hoan_tien")
        hoan = GiaoDichThanhToan.objects.get(don_hang=self.don, loai_giao_dich="hoan")
        self.assertEqual((hoan.so_tien, hoan.ma_tham_chieu), (4000, None))
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai_thanh_toan, "da_thanh_toan")  # mới hoàn một phần
        # Còn trả được 2 hộp; trả nốt thì tiền hoàn không vượt phần đã thu còn lại.
        yc2 = self.tao(so_luong=2)
        self.assertEqual(yc2.so_tien_hoan, 4000)
        with self.assertRaises(ValidationError):
            self.tao(so_luong=1)
        self.assertEqual(NhatKyEmail.objects.filter(loai_email="tra_hang").count(), 4)

    def test_kiem_so_luong_anh_va_thoi_han(self):
        with self.assertRaises(ValidationError):
            self.tao(so_luong=5)
        with self.assertRaises(ValidationError):
            self.tao(cac_anh=[])
        with self.assertRaises(PermissionDenied):
            tao_yeu_cau(
                self.d.khac,
                self.don,
                ly_do="khac",
                mo_ta="x",
                cac_dong={self.dong.pk: 1},
                cac_anh=[anh_thu()],
            )
        LichSuDonHang.objects.filter(don_hang=self.don, den_trang_thai="hoan_thanh").update(
            thoi_diem_tao=timezone.now() - timedelta(days=8)
        )
        with self.assertRaisesMessage(ValidationError, "7 ngày"):
            self.tao()

    def test_tu_choi_can_ly_do_va_cho_gui_lai(self):
        yc = self.tao()
        with self.assertRaises(ValidationError):
            tu_choi(self.d.ql, yc, "  ")
        tu_choi(self.d.ql, yc, "Hộp còn nguyên tem, không lỗi")
        self.assertEqual(YeuCauTraHang.objects.get(pk=yc.pk).trang_thai, "tu_choi")
        self.assertEqual(self.tao(so_luong=4).so_tien_hoan, 8000)

    def test_trang_web_va_anh_rieng_tu(self):
        self.client.force_login(self.d.khach)
        trang = self.client.get(reverse("ban_hang:khach_don_hang_chi_tiet", args=[self.don.pk]))
        self.assertContains(trang, "Yêu cầu trả hàng")
        url = reverse("ban_hang:khach_tra_hang", args=[self.don.pk])
        phan_hoi = self.client.post(
            url,
            {
                f"so_luong_{self.dong.pk}": 1,
                "ly_do": "het_han",
                "mo_ta": "Hạn dùng còn 1 tháng",
                "cac_anh": [anh_thu("a.png"), anh_thu("b.png")],
                "hinh_thuc_hoan_tien": "tai_quay",
            },
        )
        yc = YeuCauTraHang.objects.get()
        self.assertRedirects(
            phan_hoi, reverse("ban_hang:khach_don_hang_chi_tiet", args=[self.don.pk])
        )
        self.assertEqual(yc.cac_anh.count(), 2)
        anh = yc.cac_anh.first()
        url_anh = reverse("ban_hang:anh_tra_hang", args=[anh.pk])
        self.assertEqual(self.client.get(url_anh)["Cache-Control"], "private, no-store")
        self.client.force_login(self.d.khac)
        self.assertEqual(self.client.get(url_anh).status_code, 404)
        self.client.force_login(self.d.ql2)
        self.assertEqual(self.client.get(url_anh).status_code, 404)
        self.client.force_login(self.d.ql)
        self.assertEqual(self.client.get(url_anh).status_code, 200)
        chi_tiet = reverse("ban_hang:tra_hang_chi_tiet", args=[yc.pk])
        self.assertContains(self.client.get(chi_tiet), "Duyệt yêu cầu")
        dong = yc.cac_dong.get()
        from ..services.tra_hang import cac_lo_da_xuat

        ma_phan_bo = cac_lo_da_xuat(yc)[dong.pk][0]["phan_bo"].pk
        self.client.post(
            reverse("ban_hang:tra_hang_xu_ly", args=[yc.pk, "duyet"]),
            {f"cho_huy_{dong.pk}_{ma_phan_bo}": "1"},
        )
        self.client.post(
            reverse("ban_hang:tra_hang_xu_ly", args=[yc.pk, "hoan_tien"]),
            {"phuong_thuc": "tien_mat"},
        )
        yc.refresh_from_db()
        self.assertEqual(yc.trang_thai, "da_hoan_tien")
        self.assertContains(
            self.client.get(reverse("ban_hang:tra_hang_danh_sach") + "?trang_thai=da_hoan_tien"),
            yc.ma_yeu_cau_tra_hang,
        )


class NhanHangVaNhapLaiKhoTests(TestCase):
    """Khách xác nhận nhận hàng, tự hoàn tất quá hạn, trả hàng nhập lại đúng lô, nơi nhận tiền."""

    def setUp(self):
        from ung_dung.kho.models import TonKho

        self.TonKho = TonKho
        self.d = tao_du_lieu()
        self.ton = tao_ton(self.d, ngay=60, luong=20)
        with mock.patch("ung_dung.ban_hang.services.thong_bao_don.tep_hoa_don", return_value=None):
            self.don = dat_hang(
                self.d.khach,
                self.d.cn,
                [{"thuoc": self.d.thuoc, "so_luong": 4}],
                hinh_thuc_nhan="giao_hang",
                phuong_thuc_thanh_toan="cod",
                giao={
                    "ten_nguoi_nhan": "Khách",
                    "so_dien_thoai": "0901234567",
                    "dia_chi": "1 Lê Lợi",
                    "vi_tri": Point(106.70, 10.77, srid=4326),
                    "khoang_cach_met": 1000,
                },
            )
            xac_nhan_don(self.d.nv, self.don)
            giao_cho_van_chuyen(self.d.nv, self.don)

    def _nhan_hang(self):
        with mock.patch("ung_dung.ban_hang.services.thong_bao_don.tep_hoa_don", return_value=None):
            xac_nhan_da_giao(self.d.khach, self.don)

    def test_nhan_vien_khong_xac_nhan_thay_khach(self):
        with self.assertRaises(PermissionDenied):
            xac_nhan_da_giao(self.d.nv, self.don)
        with self.assertRaises(PermissionDenied):
            xac_nhan_da_giao(self.d.khac, self.don)
        self._nhan_hang()
        self.don.refresh_from_db()
        self.assertEqual(
            (self.don.trang_thai, self.don.trang_thai_thanh_toan), ("hoan_thanh", "chua_thanh_toan")
        )

    def test_bao_giao_that_bai_hang_hong_khong_tru_ton_lan_hai(self):
        from ung_dung.kho.models import PhieuXuatHuy

        url = reverse("ban_hang:don_hang_xu_ly", args=[self.don.pk, "giao_that_bai"])
        self.client.force_login(self.d.nv)
        du_lieu = {"ly_do": "Đơn vị giao làm hỏng hàng", "xu_ly_hang_giao": "da_huy"}
        self.client.post(url, du_lieu)
        self.assertFalse(PhieuXuatHuy.objects.exists())
        self.client.force_login(self.d.ql)
        self.client.post(url, du_lieu)
        self.client.post(url, du_lieu)
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "giao_that_bai")
        phieu = PhieuXuatHuy.objects.get()
        self.assertFalse(phieu.co_tru_ton)
        self.assertEqual(phieu.chitietphieuxuathuy_set.get().so_luong, 4)
        self.assertEqual(self.TonKho.objects.get(pk=self.ton.pk).so_luong, 16)

    def test_giao_that_bai_phan_lo_hoan_huy_that_lac(self):
        from ung_dung.bao_cao.selectors import lay_bao_cao
        from ung_dung.kho.models import PhieuXuatHuy

        from ..models import ChiTietPhieuHoanKho
        from ..selectors import lay_lo_da_xuat

        self.client.force_login(self.d.ql)
        url = reverse("ban_hang:don_hang_xu_ly", args=[self.don.pk, "giao_that_bai"])
        pb = lay_lo_da_xuat(self.don).get()
        du_lieu = {
            "ly_do": "Đơn không giao được",
            "xu_ly_hang_giao": "theo_lo",
            f"hoan_kho_{pb.pk}": "2",
            f"da_huy_{pb.pk}": "1",
        }
        self.client.post(url, du_lieu)
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "dang_giao")
        self.assertFalse(PhieuXuatHuy.objects.exists())
        self.client.post(url, {**du_lieu, f"that_lac_{pb.pk}": "1"})
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "giao_that_bai")
        self.assertEqual(ChiTietPhieuHoanKho.objects.get().so_luong, 2)
        self.assertEqual(PhieuXuatHuy.objects.get().chitietphieuxuathuy_set.get().so_luong, 1)
        self.assertEqual(self.TonKho.objects.get(pk=self.ton.pk).so_luong, 18)
        self.assertIn("Thất lạc", self.don.cac_lich_su.latest("pk").ghi_chu)
        ngay = timezone.localdate()
        self.assertEqual(lay_bao_cao(self.d.ql, ngay, ngay)["doanh_thu_thuan"], 0)

    def test_qua_ba_ngay_van_can_xac_nhan_giao_thuc_te(self):
        from ..services.don_hang import xac_nhan_giao_thanh_cong, xu_ly_qua_han

        LichSuDonHang.objects.filter(don_hang=self.don, den_trang_thai="dang_giao").update(
            thoi_diem_tao=timezone.now() - timedelta(days=3, minutes=1)
        )
        self.assertEqual(xu_ly_qua_han(), 0)
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "dang_giao")
        with self.assertRaises(ValidationError):
            xac_nhan_giao_thanh_cong(self.d.nv, self.don, "")
        xac_nhan_giao_thanh_cong(self.d.nv, self.don, "Biên nhận thử GN-01")
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "hoan_thanh")
        self.assertIn("GN-01", LichSuDonHang.objects.filter(don_hang=self.don).latest("pk").ghi_chu)

    def test_nut_doi_chieu_giao_chi_hien_khi_don_dang_giao(self):
        from ..services.don_hang import xac_nhan_giao_thanh_cong
        from ..views.don_hang import cac_hanh_dong

        ma = lambda: {h["ma"] for h in cac_hanh_dong(self.don, self.d.nv)}  # noqa: E731
        self.don.refresh_from_db()
        self.assertIn("xac_nhan_giao_thanh_cong", ma())
        # Đơn giữ tại quầy hoàn thành bằng "Khách đã nhận", không qua đối chiếu giao nhận.
        self.don.trang_thai = "dang_giu"
        self.assertNotIn("xac_nhan_giao_thanh_cong", ma())
        with self.assertRaises(ValidationError):
            xac_nhan_giao_thanh_cong(self.d.nv, self.don, "GN-02")

    def _tra(self, ly_do, so_luong, hoan_tien=None):
        return tao_yeu_cau(
            self.d.khach,
            self.don,
            ly_do=ly_do,
            mo_ta="Giao nhầm thuốc",
            cac_dong={self.don.cac_dong.get().pk: so_luong},
            cac_anh=[anh_thu()],
            hoan_tien=hoan_tien,
        )

    def test_hang_giao_nham_duoc_cach_ly_va_huy_theo_lo(self):
        self._nhan_hang()
        self.assertEqual(self.TonKho.objects.get(pk=self.ton.pk).so_luong, 16)
        yc = self._tra(
            "sai_san_pham",
            3,
            {"hinh_thuc_hoan_tien": "momo", "so_dien_thoai_momo": "0901234567"},
        )
        duyet(self.d.ql, yc, "Nhận lại 3 hộp còn tem")
        self.assertEqual(self.TonKho.objects.get(pk=self.ton.pk).so_luong, 16)
        dong = yc.cac_dong.get()
        self.assertEqual(dong.so_luong_nhap_lai, 0)
        cho_huy = dong.cac_hang_cho_huy.get()
        self.assertEqual(cho_huy.phan_bo_phieu_ban.ton_kho_id, self.ton.pk)
        self.client.force_login(self.d.ql)
        url = reverse("ban_hang:tra_hang_huy", args=[yc.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        cho_huy.refresh_from_db()
        self.assertEqual(cho_huy.trang_thai, "da_huy")
        self.assertEqual(cho_huy.phieu_xuat_huy.chitietphieuxuathuy_set.get().so_luong, 3)
        self.assertEqual(self.TonKho.objects.get(pk=self.ton.pk).so_luong, 16)

    def test_hang_hu_hong_khong_nhap_lai_va_khong_vuot_so_tra(self):
        self._nhan_hang()
        yc = self._tra("hu_hong", 2)
        dong = yc.cac_dong.get()
        from ..services.tra_hang import cac_lo_da_xuat

        ma_phan_bo = cac_lo_da_xuat(yc)[dong.pk][0]["phan_bo"].pk
        with self.assertRaises(ValidationError):
            duyet(self.d.ql, yc, phan_lo={(dong.pk, ma_phan_bo): 3})
        duyet(self.d.ql, yc)
        self.assertEqual(self.TonKho.objects.get(pk=self.ton.pk).so_luong, 16)
        self.assertEqual(yc.cac_dong.get().so_luong_nhap_lai, 0)

    def test_thong_tin_nhan_tien_hoan_dung_hinh_thuc(self):
        self._nhan_hang()
        with self.assertRaises(ValidationError):
            self._tra("hu_hong", 1, {"hinh_thuc_hoan_tien": "chuyen_khoan", "ten_ngan_hang": "ACB"})
        yc = self._tra(
            "hu_hong",
            1,
            {
                "hinh_thuc_hoan_tien": "chuyen_khoan",
                "ten_ngan_hang": "Vietcombank",
                "so_tai_khoan": "0071000123456",
                "ten_chu_tai_khoan": "NGUYEN VAN A",
            },
        )
        self.assertEqual(yc.get_hinh_thuc_hoan_tien_display(), "Chuyển khoản ngân hàng")

    def test_form_khach_chuan_hoa_tai_khoan_va_hien_anh(self):
        self._nhan_hang()
        self.client.force_login(self.d.khach)
        dong = self.don.cac_dong.get()
        url = reverse("ban_hang:khach_tra_hang", args=[self.don.pk])
        trang = self.client.get(url)
        self.assertContains(trang, "data-xem-truoc")
        self.assertContains(trang, "Nhận tiền hoàn qua")
        phan_hoi = self.client.post(
            url,
            {
                f"so_luong_{dong.pk}": 1,
                "ly_do": "hu_hong",
                "mo_ta": "Vỉ rách",
                "cac_anh": [anh_thu()],
                "hinh_thuc_hoan_tien": "chuyen_khoan",
                "ten_ngan_hang": "Techcombank",
                "so_tai_khoan": "1903 1234 5678",
                "ten_chu_tai_khoan": "Nguyễn Thị Ánh Đào",
            },
        )
        self.assertEqual(phan_hoi.status_code, 302)
        yc = YeuCauTraHang.objects.get()
        self.assertEqual(
            (yc.so_tai_khoan, yc.ten_chu_tai_khoan), ("190312345678", "NGUYEN THI ANH DAO")
        )
        chi_tiet = self.client.get(reverse("ban_hang:khach_don_hang_chi_tiet", args=[self.don.pk]))
        self.assertContains(chi_tiet, reverse("ban_hang:anh_tra_hang", args=[yc.cac_anh.get().pk]))
