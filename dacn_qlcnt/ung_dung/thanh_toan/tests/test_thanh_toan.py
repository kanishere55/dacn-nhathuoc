import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.gis.geos import Point
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ung_dung.ban_hang.models import DonHang
from ung_dung.ban_hang.services.dat_hang import dat_hang
from ung_dung.ban_hang.services.don_hang import (
    giao_cho_van_chuyen,
    huy_don,
    xac_nhan_da_giao,
    xac_nhan_don,
)
from ung_dung.ban_hang.services.phieu_ban import ban_tai_quay
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton

from .. import momo, vietqr
from ..models import GiaoDichThanhToan
from ..selectors import phuong_thuc_kha_dung
from ..services.cong import hoan_tien, xac_nhan_tay, xu_ly_ket_qua_momo, xu_ly_sepay

NGAN_HANG = {
    "NGAN_HANG_BIN": "970436",
    "SO_TAI_KHOAN": "0123456789",
    "TEN_TAI_KHOAN": "NHA THUOC THU",
    "TEN_NGAN_HANG": "Vietcombank",
    "SEPAY_API_KEY": "khoa-thu-sepay",
}
MOMO = {
    "MOMO_PARTNER_CODE": "MOMOTHU",
    "MOMO_ACCESS_KEY": "truy-cap-thu",
    "MOMO_SECRET_KEY": "bi-mat-thu",
}


def giao():
    return {
        "ten_nguoi_nhan": "Người nhận",
        "so_dien_thoai": "0901234567",
        "dia_chi": "1 Lê Lợi, Quận 1",
        "vi_tri": Point(106.701, 10.771, srid=4326),
        "khoang_cach_met": 1200,
    }


class VietQRTests(TestCase):
    def test_crc_dung_vector_chuan(self):
        self.assertEqual(vietqr.crc16_ccitt("123456789"), "29B1")

    def test_chuoi_co_du_truong_va_crc_khop(self):
        chuoi = vietqr.tao_chuoi("970436", "0123456789", Decimal("45000"), "DHABC-123")
        self.assertTrue(chuoi.startswith("000201010212"))
        self.assertIn("0010A000000727", chuoi)
        self.assertIn("0208QRIBFTTA", chuoi)
        self.assertIn("5303704540545000", chuoi)
        self.assertIn("0808DHABC123", chuoi)
        self.assertEqual(chuoi[-4:], vietqr.crc16_ccitt(chuoi[:-4]))
        self.assertIn("<svg", vietqr.ve_svg(chuoi))

    def test_cau_hinh_sai_bi_tu_choi(self):
        with self.assertRaises(ValueError):
            vietqr.tao_chuoi("97043", "0123456789", 1000, "DH1")


@override_settings(**NGAN_HANG)
class ChuyenKhoanTests(TestCase):
    def setUp(self):
        self.d = tao_du_lieu()
        tao_ton(self.d, luong=20)
        self.don = dat_hang(
            self.d.khach,
            self.d.cn,
            [{"thuoc": self.d.thuoc, "so_luong": 2}],
            hinh_thuc_nhan="giao_hang",
            phuong_thuc_thanh_toan="chuyen_khoan",
            giao=giao(),
        )

    def sepay(self, so_tien=None, ma="1001", noi_dung=None, loai="in"):
        return {
            "id": ma,
            "transferType": loai,
            "transferAmount": int(so_tien if so_tien is not None else self.don.tong_thanh_toan),
            "content": noi_dung or f"CK {self.don.ma_don_hang.lower()} thanh toan",
            "code": None,
        }

    def test_dat_don_tao_giao_dich_cho_va_chuyen_trang_thanh_toan(self):
        self.assertEqual(self.don.trang_thai, "cho_thanh_toan")
        cho = GiaoDichThanhToan.objects.get(don_hang=self.don)
        self.assertEqual((cho.trang_thai, cho.so_tien), ("cho", self.don.tong_thanh_toan))
        self.assertEqual(phuong_thuc_kha_dung(), {"cod", "chuyen_khoan"})
        self.client.force_login(self.d.khach)
        phan_hoi = self.client.get(reverse("thanh_toan:trang_thanh_toan", args=[self.don.pk]))
        self.assertContains(phan_hoi, "<svg")
        self.assertContains(phan_hoi, self.don.ma_don_hang)
        self.client.force_login(self.d.khac)
        phan_hoi = self.client.get(reverse("thanh_toan:trang_thanh_toan", args=[self.don.pk]))
        self.assertEqual(phan_hoi.status_code, 404)

    def test_anh_qr_png_chi_chu_don_tai_duoc(self):
        url = reverse("thanh_toan:anh_qr", args=[self.don.pk])
        self.client.force_login(self.d.khach)
        phan_hoi = self.client.get(url)
        self.assertEqual(phan_hoi["Content-Type"], "image/png")
        self.assertTrue(phan_hoi.content.startswith(b"\x89PNG"))
        self.client.force_login(self.d.khac)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_webhook_can_khoa_va_chi_ghi_mot_lan(self):
        url = reverse("thanh_toan:sepay_webhook")
        than = json.dumps(self.sepay())
        sai = self.client.post(url, than, content_type="application/json")
        self.assertEqual(sai.status_code, 401)
        for _ in range(2):
            phan_hoi = self.client.post(
                url,
                than,
                content_type="application/json",
                HTTP_AUTHORIZATION="Apikey khoa-thu-sepay",
            )
            self.assertEqual(phan_hoi.status_code, 200)
        self.don.refresh_from_db()
        self.assertEqual(
            (self.don.trang_thai, self.don.trang_thai_thanh_toan),
            ("cho_xac_nhan", "da_thanh_toan"),
        )
        self.assertEqual(
            list(
                GiaoDichThanhToan.objects.filter(don_hang=self.don).values_list(
                    "trang_thai", "ma_tham_chieu"
                )
            ),
            [("thanh_cong", "sepay-1001")],
        )
        self.assertEqual(json.loads(phan_hoi.content)["ket_qua"], "trung")

    def test_ma_don_ngan_va_tim_duoc_trong_noi_dung_ngan_hang(self):
        self.assertRegex(self.don.ma_don_hang, r"^DH\d{6}[2-9A-HJKMNP-Z]{5}$")
        noi_dung = f"MBVCB.8842.{self.don.ma_don_hang.lower()}.CT tu 0123 toi 0456"
        self.assertEqual(xu_ly_sepay(self.sepay(noi_dung=noi_dung)), "da_ghi")
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "cho_xac_nhan")

    def test_tien_ra_hoac_khong_co_ma_don_bi_bo_qua(self):
        self.assertEqual(xu_ly_sepay(self.sepay(loai="out")), "bo_qua")
        self.assertEqual(xu_ly_sepay(self.sepay(noi_dung="chuyen tien an trua")), "khong_khop")
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "cho_thanh_toan")

    def test_chuyen_thieu_giu_don_cho_thanh_toan(self):
        self.assertEqual(xu_ly_sepay(self.sepay(so_tien=1000)), "da_ghi")
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "cho_thanh_toan")
        thieu = GiaoDichThanhToan.objects.get(don_hang=self.don, trang_thai="thanh_cong")
        self.assertIn("thiếu", thieu.ghi_chu)

    def test_tien_den_sau_han_huy_don_va_cho_hoan(self):
        DonHang.objects.filter(pk=self.don.pk).update(
            thoi_diem_tao=timezone.now() - timedelta(minutes=40),
            thoi_diem_het_giu=timezone.now() - timedelta(minutes=10),
        )
        self.assertEqual(xu_ly_sepay(self.sepay()), "da_ghi")
        self.don.refresh_from_db()
        self.assertEqual(
            (self.don.trang_thai, self.don.trang_thai_thanh_toan), ("da_huy", "cho_hoan_tien")
        )

    def test_huy_sau_khi_tra_thi_hoan_tien_dung_so_da_thu(self):
        xu_ly_sepay(self.sepay())
        huy_don(self.d.khach, self.don, "Đổi ý")
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai_thanh_toan, "cho_hoan_tien")
        with self.assertRaises(PermissionDenied):
            hoan_tien(self.d.nv, self.don, phuong_thuc="chuyen_khoan", ma_tham_chieu="FT1")
        hoan_tien(self.d.ql, self.don, phuong_thuc="chuyen_khoan", ma_tham_chieu="FT1")
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai_thanh_toan, "da_hoan_tien")
        hoan = GiaoDichThanhToan.objects.get(don_hang=self.don, loai_giao_dich="hoan")
        self.assertEqual(hoan.so_tien, self.don.tong_thanh_toan)
        with self.assertRaises(ValidationError):
            hoan_tien(self.d.ql, self.don, phuong_thuc="chuyen_khoan")

    def test_nhan_vien_xac_nhan_tay_dung_chi_nhanh(self):
        with self.assertRaises(PermissionDenied):
            xac_nhan_tay(self.d.ql2, self.don, "FT2")
        xac_nhan_tay(self.d.nv, self.don, "FT2")
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "cho_xac_nhan")
        with self.assertRaises(ValidationError):
            xac_nhan_tay(self.d.nv, self.don, "FT3")

    def test_trang_thai_htmx_chuyen_trang_khi_da_tra(self):
        self.client.force_login(self.d.khach)
        url = reverse("thanh_toan:trang_thai", args=[self.don.pk])
        self.assertNotIn("HX-Redirect", self.client.get(url))
        xu_ly_sepay(self.sepay())
        self.assertIn("HX-Redirect", self.client.get(url))


@override_settings(**MOMO)
class MoMoTests(TestCase):
    def setUp(self):
        self.d = tao_du_lieu()
        tao_ton(self.d, luong=20)
        self.don = dat_hang(
            self.d.khach,
            self.d.cn,
            [{"thuoc": self.d.thuoc, "so_luong": 1}],
            hinh_thuc_nhan="giao_hang",
            phuong_thuc_thanh_toan="momo",
            giao=giao(),
        )
        self.gd = GiaoDichThanhToan.objects.get(don_hang=self.don)

    def ket_qua(self, ma_ket_qua=0, so_tien=None):
        du_lieu = {
            "partnerCode": "MOMOTHU",
            "orderId": self.gd.ma_giao_dich_thanh_toan,
            "requestId": self.gd.ma_giao_dich_thanh_toan,
            "amount": str(int(so_tien or self.don.tong_thanh_toan)),
            "orderInfo": "Thanh toan",
            "orderType": "momo_wallet",
            "transId": "4088878653",
            "resultCode": str(ma_ket_qua),
            "message": "Thành công." if ma_ket_qua == 0 else "Giao dịch bị từ chối.",
            "payType": "qr",
            "responseTime": "1721720663942",
            "extraData": "",
        }
        du_lieu["signature"] = momo.ky(
            [("accessKey", "truy-cap-thu")]
            + [(ten, du_lieu[ten]) for ten in momo.TRUONG_KY_KET_QUA[1:]]
        )
        return du_lieu

    def test_ipn_sai_chu_ky_bi_tu_choi(self):
        du_lieu = self.ket_qua()
        du_lieu["amount"] = "1"
        phan_hoi = self.client.post(
            reverse("thanh_toan:momo_ipn"), json.dumps(du_lieu), content_type="application/json"
        )
        self.assertEqual(phan_hoi.status_code, 400)
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "cho_thanh_toan")

    def test_ipn_thanh_cong_va_trang_quay_ve_khong_ghi_lap(self):
        phan_hoi = self.client.post(
            reverse("thanh_toan:momo_ipn"),
            json.dumps(self.ket_qua()),
            content_type="application/json",
        )
        self.assertEqual(phan_hoi.status_code, 204)
        self.client.force_login(self.d.khach)
        quay_ve = self.client.get(reverse("thanh_toan:momo_quay_ve"), self.ket_qua())
        self.assertRedirects(
            quay_ve, reverse("ban_hang:khach_don_hang_chi_tiet", args=[self.don.pk])
        )
        self.don.refresh_from_db()
        self.assertEqual(self.don.trang_thai, "cho_xac_nhan")
        self.assertEqual(
            GiaoDichThanhToan.objects.filter(don_hang=self.don, trang_thai="thanh_cong").count(), 1
        )

    def test_that_bai_giu_don_cho_thanh_toan(self):
        self.assertEqual(xu_ly_ket_qua_momo(self.ket_qua(ma_ket_qua=1006)), "that_bai")
        self.gd.refresh_from_db()
        self.don.refresh_from_db()
        self.assertEqual((self.gd.trang_thai, self.don.trang_thai), ("that_bai", "cho_thanh_toan"))


class TaiQuayVaCodTests(TestCase):
    def setUp(self):
        self.d = tao_du_lieu()
        tao_ton(self.d, luong=20)

    def test_ban_truc_tiep_ghi_khoan_thu(self):
        phieu = ban_tai_quay(
            self.d.nv,
            self.d.cn,
            [{"thuoc": self.d.thuoc, "so_luong": 3}],
            phuong_thuc_thanh_toan="chuyen_khoan",
        )
        gd = GiaoDichThanhToan.objects.get(phieu_ban=phieu)
        self.assertEqual((gd.phuong_thuc, gd.so_tien), ("chuyen_khoan", 6000))
        with self.assertRaises(ValidationError):
            ban_tai_quay(
                self.d.nv,
                self.d.cn,
                [{"thuoc": self.d.thuoc, "so_luong": 1}],
                phuong_thuc_thanh_toan="momo",
            )

    def test_cod_ghi_khi_giao_xong(self):
        don = dat_hang(
            self.d.khach,
            self.d.cn,
            [{"thuoc": self.d.thuoc, "so_luong": 2}],
            hinh_thuc_nhan="giao_hang",
            phuong_thuc_thanh_toan="cod",
            giao=giao(),
        )
        self.assertFalse(GiaoDichThanhToan.objects.filter(don_hang=don).exists())
        xac_nhan_don(self.d.nv, don)
        giao_cho_van_chuyen(self.d.nv, don)
        xac_nhan_da_giao(self.d.nv, don)
        gd = GiaoDichThanhToan.objects.get(don_hang=don)
        self.assertEqual((gd.phuong_thuc, gd.so_tien), ("cod", don.tong_thanh_toan))

    def test_phuong_thuc_tra_truoc_an_khi_chua_cau_hinh(self):
        self.assertEqual(phuong_thuc_kha_dung(), {"cod"})


class ThuocKeDonTests(TestCase):
    def setUp(self):
        self.d = tao_du_lieu()
        self.d.thuoc.la_thuoc_ke_don = True
        self.d.thuoc.save()
        tao_ton(self.d, luong=20)
        self.dong = [{"thuoc": self.d.thuoc, "so_luong": 1}]

    def test_bat_buoc_ghi_bac_si_va_co_so(self):
        for thieu in (
            {},
            {"da_kiem_tra_don_thuoc": True, "ten_nguoi_ke_don": "BS. An"},
            {"ten_nguoi_ke_don": "BS. An", "noi_kham_benh": "BV Chợ Rẫy"},
            {
                "da_kiem_tra_don_thuoc": True,
                "ten_nguoi_ke_don": "BS. An",
                "noi_kham_benh": "BV Chợ Rẫy",
                "ma_don_thuoc": "ma sai!",
            },
        ):
            with self.subTest(thieu=thieu), self.assertRaises(ValidationError):
                ban_tai_quay(self.d.nv, self.d.cn, self.dong, don_thuoc=thieu)
        phieu = ban_tai_quay(
            self.d.nv,
            self.d.cn,
            self.dong,
            don_thuoc={
                "da_kiem_tra_don_thuoc": True,
                "ten_nguoi_ke_don": "  BS.  Trần An ",
                "noi_kham_benh": "Bệnh viện Chợ Rẫy",
                "ma_don_thuoc": "79001ab12cd3-c",
            },
        )
        self.assertEqual(
            (phieu.ten_nguoi_ke_don, phieu.ma_don_thuoc, phieu.da_kiem_tra_don_thuoc),
            ("BS. Trần An", "79001ab12cd3-c", True),
        )

    def test_thuoc_khong_ke_don_bo_qua_thong_tin_don(self):
        self.d.thuoc.la_thuoc_ke_don = False
        self.d.thuoc.save()
        phieu = ban_tai_quay(
            self.d.nv, self.d.cn, self.dong, don_thuoc={"ten_nguoi_ke_don": "BS. An"}
        )
        self.assertEqual((phieu.ten_nguoi_ke_don, phieu.da_kiem_tra_don_thuoc), ("", False))
