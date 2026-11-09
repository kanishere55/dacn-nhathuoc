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
        tao_ton(self.d, luong=20)
        with mock.patch(
            "ung_dung.ban_hang.services.thong_bao_don._hoa_don_dinh_kem", return_value=()
        ):
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
            xac_nhan_da_giao(self.d.nv, self.don)
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
        hoan_tien_tra_hang(self.d.ql, yc, phuong_thuc="chuyen_khoan", ma_tham_chieu="FT77")
        yc.refresh_from_db()
        self.assertEqual(yc.trang_thai, "da_hoan_tien")
        hoan = GiaoDichThanhToan.objects.get(don_hang=self.don, loai_giao_dich="hoan")
        self.assertEqual((hoan.so_tien, hoan.ma_tham_chieu), (4000, "tra-FT77"))
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
        self.client.post(reverse("ban_hang:tra_hang_xu_ly", args=[yc.pk, "duyet"]), {"ghi_chu": ""})
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
