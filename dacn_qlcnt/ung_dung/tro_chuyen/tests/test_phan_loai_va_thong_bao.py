"""Một cuộc trò chuyện cho mỗi khách – chi nhánh (kiểu Shopee), thẻ sản phẩm / đơn hàng, ảnh đính
kèm, mốc đã đọc, số chưa đọc, thông báo thời gian thực, nút tư vấn nổi."""

from io import BytesIO
from uuid import uuid4

from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from PIL import Image

from ung_dung.ban_hang.services.dat_hang import dat_hang
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton

from ..models import AnhTinNhan, CuocTroChuyen, TinNhan
from ..routing import websocket_urlpatterns
from ..selectors import dem_chua_doc, lay_hop_thu, lay_tin_cu
from ..services import (
    GIOI_HAN_TIN_MOT_PHUT,
    bat_dau_tro_chuyen,
    bat_dau_ve_don,
    danh_dau_da_doc,
    danh_dau_xong,
    ghi_tin_nhan,
    mo_phong,
)

KENH_BO_NHO = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def tao_don(d):
    tao_ton(d, luong=20)
    return dat_hang(
        d.khach,
        d.cn,
        [{"thuoc": d.thuoc, "so_luong": 1}],
        hinh_thuc_nhan="nhan_tai_quay",
        phuong_thuc_thanh_toan="tai_quay",
    )


def anh_png(ten="anh.png"):
    dau_ra = BytesIO()
    Image.new("RGB", (40, 30), (200, 30, 30)).save(dau_ra, "PNG")
    return SimpleUploadedFile(ten, dau_ra.getvalue(), content_type="image/png")


class NghiepVuTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        cls.don = tao_don(cls.d)

    def test_moi_khach_chi_mot_cuoc_tro_chuyen_voi_moi_chi_nhanh(self):
        d = self.d
        phong = bat_dau_tro_chuyen(d.khach, d.cn, "Còn Panadol không?", thuoc=d.thuoc)
        # Hỏi về đơn, hỏi sản phẩm hay nhắn thẳng đều vào cùng một cuộc với chi nhánh đó.
        self.assertEqual(bat_dau_ve_don(d.khach, self.don, "Đơn này khi nào có?"), phong)
        self.assertEqual(bat_dau_ve_don(d.nv, self.don, "Chiều nay có ạ"), phong)
        self.assertEqual(bat_dau_tro_chuyen(d.khach, d.cn, "Cảm ơn"), phong)
        self.assertEqual(CuocTroChuyen.objects.count(), 1)
        the = list(TinNhan.objects.order_by("pk").values_list("thuoc_id", "don_hang_id"))
        self.assertEqual(
            the, [(d.thuoc.pk, None), (None, self.don.pk), (None, self.don.pk), (None, None)]
        )
        lich_su = lay_tin_cu(d.khach, phong)["cac_tin"]
        self.assertEqual(lich_su[0]["the"]["loai"], "thuoc")
        self.assertEqual(lich_su[1]["the"]["ten"], f"Đơn {self.don.ma_don_hang}")
        self.assertIsNone(lich_su[3]["the"])
        # Chi nhánh khác là cuộc trò chuyện khác.
        self.assertNotEqual(bat_dau_tro_chuyen(d.khach, d.cn2, "Chi nhánh 2 còn không?"), phong)
        with self.assertRaises(PermissionDenied):
            bat_dau_ve_don(d.khac, self.don, "Spam")
        with self.assertRaises(PermissionDenied):
            bat_dau_ve_don(d.ql2, self.don, "Chi nhánh khác")

    def test_the_don_phai_dung_khach_va_chi_nhanh(self):
        d = self.d
        phong_khac = mo_phong(d.khac, d.cn)
        with self.assertRaises(ValidationError):
            ghi_tin_nhan(d.khac, phong_khac, str(uuid4()), "Đơn người khác", don=self.don)
        with self.assertRaises(ValidationError):
            ghi_tin_nhan(
                d.khach,
                mo_phong(d.khach, d.cn),
                str(uuid4()),
                "Hai thẻ",
                thuoc=d.thuoc,
                don=self.don,
            )
        self.assertFalse(TinNhan.objects.exists())

    def test_rang_buoc_csdl(self):
        phong = mo_phong(self.d.khach, self.d.cn)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CuocTroChuyen.objects.create(khach_hang=self.d.khach, chi_nhanh=self.d.cn)
        with self.assertRaises(IntegrityError), transaction.atomic():
            TinNhan.objects.create(
                cuoc_tro_chuyen=phong, nguoi_gui=self.d.khach, ma_tin_nhan=str(uuid4())
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            TinNhan.objects.create(
                cuoc_tro_chuyen=phong,
                nguoi_gui=self.d.khach,
                ma_tin_nhan=str(uuid4()),
                noi_dung_tin_nhan="Hai thẻ",
                thuoc=self.d.thuoc,
                don_hang=self.don,
            )

    def test_tin_kem_anh(self):
        d = self.d
        phong = mo_phong(d.khach, d.cn)
        tin, _ = ghi_tin_nhan(d.khach, phong, str(uuid4()), "", cac_anh=[anh_png(), anh_png()])
        self.assertEqual((tin.so_anh, tin.noi_dung_tin_nhan), (2, ""))
        self.assertEqual(list(tin.cac_anh.values_list("thu_tu", flat=True)), [0, 1])
        self.assertEqual(len(lay_tin_cu(d.nv, phong)["cac_tin"][0]["anh"]), 2)
        self.assertEqual(lay_hop_thu(d.nv).get().so_anh_cuoi, 2)
        with self.assertRaises(ValidationError):
            ghi_tin_nhan(d.khach, phong, str(uuid4()), "", cac_anh=[anh_png() for _ in range(6)])
        gia = SimpleUploadedFile("gia.png", b"khong phai anh", content_type="image/png")
        with self.assertRaises(ValidationError):
            ghi_tin_nhan(d.khach, phong, str(uuid4()), "Ảnh giả", cac_anh=[gia])
        with self.assertRaises(ValidationError):
            ghi_tin_nhan(d.khach, phong, str(uuid4()), "   ")
        # Tin lỗi không để lại gì.
        self.assertEqual((TinNhan.objects.count(), AnhTinNhan.objects.count()), (1, 2))
        with self.assertRaises(IntegrityError), transaction.atomic():
            anh = AnhTinNhan(tin_nhan=tin, thu_tu=5)
            anh.gan_du_lieu(anh_png())
            anh.save()

    def test_moc_da_doc_va_so_chua_doc_hai_phia(self):
        d = self.d
        phong = mo_phong(d.khach, d.cn)
        tin_khach, _ = ghi_tin_nhan(d.khach, phong, str(uuid4()), "Còn Panadol không ạ?")
        phong.refresh_from_db()
        self.assertEqual(phong.tin_khach_da_doc_id, tin_khach.pk)
        self.assertEqual((dem_chua_doc(d.nv), dem_chua_doc(d.khach)), (1, 0))
        self.assertEqual(lay_hop_thu(d.nv, "cho_tra_loi").get().so_chua_doc, 1)
        self.assertEqual(danh_dau_da_doc(d.nv, phong, tin_khach.pk), ("nha_thuoc", tin_khach.pk))
        self.assertIsNone(danh_dau_da_doc(d.nv, phong, tin_khach.pk))
        self.assertEqual(dem_chua_doc(d.nv), 0)
        tra_loi, _ = ghi_tin_nhan(d.nv, phong, str(uuid4()), "Dạ còn ạ")
        self.assertEqual((dem_chua_doc(d.khach), dem_chua_doc(d.nv)), (1, 0))
        self.assertFalse(lay_hop_thu(d.nv, "cho_tra_loi").exists())
        # Mốc không lùi và không trỏ sang tin của cuộc trò chuyện khác.
        danh_dau_da_doc(d.khach, phong, tra_loi.pk)
        self.assertIsNone(danh_dau_da_doc(d.khach, phong, tin_khach.pk))
        phong_khac = mo_phong(d.khach, d.cn2)
        tin_khac, _ = ghi_tin_nhan(d.khach, phong_khac, str(uuid4()), "Hỏi chi nhánh 2")
        with self.assertRaises(ValidationError):
            danh_dau_da_doc(d.khach, phong, tin_khac.pk)
        self.assertEqual(lay_hop_thu(d.nv, "da_tra_loi").get(), phong)
        # Nhân sự chi nhánh khác chỉ đếm tin của chi nhánh mình.
        self.assertEqual(dem_chua_doc(d.ql2), 1)


class BatDauVaHangChoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        cls.don = tao_don(cls.d)

    def test_phong_chi_sinh_ra_cung_tin_dau(self):
        d = self.d
        with self.assertRaises(ValidationError):
            bat_dau_ve_don(d.khach, self.don, "   ")
        self.assertFalse(CuocTroChuyen.objects.exists())
        phong = bat_dau_ve_don(d.khach, self.don, "Khi nào nhận được hàng?")
        self.assertEqual(phong.tin_cuoi.noi_dung_tin_nhan, "Khi nào nhận được hàng?")
        self.assertEqual(CuocTroChuyen.objects.count(), 1)

    def test_gioi_han_toc_do_chi_ap_cho_khach(self):
        d = self.d
        phong = bat_dau_tro_chuyen(d.khach, d.cn, "Tin 1")
        for i in range(GIOI_HAN_TIN_MOT_PHUT - 1):
            ghi_tin_nhan(d.khach, phong, str(uuid4()), f"Tin {i + 2}")
        with self.assertRaises(ValidationError):
            ghi_tin_nhan(d.khach, phong, str(uuid4()), "Tin quá nhanh")
        for i in range(GIOI_HAN_TIN_MOT_PHUT + 2):
            ghi_tin_nhan(d.nv, phong, str(uuid4()), f"Trả lời {i}")

    def test_da_xong_roi_hang_cho_va_tu_mo_lai(self):
        d = self.d
        phong = bat_dau_tro_chuyen(d.khach, d.cn, "Hỏi thuốc ho")
        self.assertEqual(list(lay_hop_thu(d.nv, "cho_tra_loi")), [phong])
        with self.assertRaises(PermissionDenied):
            danh_dau_xong(d.khach, phong)
        danh_dau_xong(d.nv, phong)
        self.assertFalse(lay_hop_thu(d.nv, "cho_tra_loi").exists())
        self.assertEqual(lay_hop_thu(d.nv, "da_xong").get().nguoi_danh_dau_xong, d.nv)
        ghi_tin_nhan(d.khach, phong, str(uuid4()), "Cho em hỏi thêm")
        phong.refresh_from_db()
        self.assertEqual(
            (phong.trang_thai_xu_ly, phong.thoi_diem_xong, phong.nguoi_danh_dau_xong),
            ("dang_mo", None, None),
        )
        self.assertEqual(list(lay_hop_thu(d.nv, "cho_tra_loi")), [phong])

    def test_lich_su_tai_dan(self):
        d = self.d
        phong = bat_dau_tro_chuyen(d.khach, d.cn, "Tin đầu")
        for i in range(40):
            ghi_tin_nhan(d.nv, phong, str(uuid4()), f"Trả lời {i}")
        trang_dau = lay_tin_cu(d.khach, phong)
        self.assertEqual((len(trang_dau["cac_tin"]), trang_dau["con_nua"]), (30, True))
        cu_hon = lay_tin_cu(d.khach, phong, trang_dau["cac_tin"][0]["id_tin_nhan"])
        self.assertEqual((len(cu_hon["cac_tin"]), cu_hon["con_nua"]), (11, False))
        self.assertEqual(cu_hon["cac_tin"][0]["noi_dung"], "Tin đầu")
        self.client.force_login(d.khach)
        json = self.client.get(
            reverse("tro_chuyen:khach_tin_cu", args=[phong.pk]),
            {"truoc": trang_dau["cac_tin"][0]["id_tin_nhan"]},
        ).json()
        self.assertEqual(len(json["cac_tin"]), 11)
        self.client.force_login(d.khac)
        self.assertEqual(
            self.client.get(reverse("tro_chuyen:khach_tin_cu", args=[phong.pk])).status_code, 404
        )


class GiaoDienTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        cls.don = tao_don(cls.d)

    def test_khach_hoi_duoc_si_tu_san_pham_va_tu_don(self):
        d = self.d
        self.client.force_login(d.khach)
        url = reverse("tro_chuyen:khach_danh_sach")
        trang = self.client.get(url, {"thuoc": d.thuoc.ma_thuoc})
        self.assertContains(trang, "Bạn đang hỏi về sản phẩm này")
        self.assertEqual(trang.context["form"]["chi_nhanh"].value(), d.cn.pk)
        phan_hoi = self.client.post(
            url,
            {
                "chi_nhanh": d.cn.pk,
                "noi_dung": "Thuốc này trẻ em dùng được không?",
                "thuoc": d.thuoc.ma_thuoc,
                "nhung": "1",
            },
        )
        phong = CuocTroChuyen.objects.get()
        url_phong = reverse("tro_chuyen:khach_chi_tiet", args=[phong.pk])
        self.assertRedirects(phan_hoi, url_phong + "?nhung=1")
        self.assertEqual(TinNhan.objects.get().thuoc, d.thuoc)
        nhung = self.client.get(url_phong + "?nhung=1")
        self.assertEqual(nhung["X-Frame-Options"], "SAMEORIGIN")
        self.assertNotContains(nhung, "chan-trang-khach")
        self.assertContains(nhung, "Đang hỏi về sản phẩm")
        # Hỏi sản phẩm lần sau: mở thẳng cuộc trò chuyện cũ, thẻ chờ sẵn ở khung soạn tin.
        lan_sau = self.client.get(url, {"thuoc": d.thuoc.ma_thuoc})
        self.assertRedirects(lan_sau, url_phong + f"?thuoc={d.thuoc.ma_thuoc}")
        self.assertContains(self.client.get(lan_sau["Location"]), "data-the-cho")
        # Tin trống và không ảnh không tạo gì.
        loi = self.client.post(url, {"chi_nhanh": d.cn.pk, "noi_dung": ""})
        self.assertContains(loi, "Hãy nhập nội dung tin nhắn hoặc chọn ảnh.")
        # Hỏi về đơn khi đã có cuộc trò chuyện với chi nhánh: vào cuộc đó kèm thẻ đơn.
        url_don = reverse("tro_chuyen:khach_tu_don_hang", args=[self.don.pk])
        tu_don = self.client.get(url_don)
        self.assertRedirects(tu_don, url_phong + f"?don={self.don.pk}")
        self.assertContains(self.client.get(tu_don["Location"]), "Bạn đang hỏi về đơn hàng này")
        self.assertEqual(CuocTroChuyen.objects.count(), 1)
        self.client.force_login(d.khac)
        self.assertEqual(self.client.post(url_don).status_code, 404)

    def test_khach_chua_tung_nhan_hoi_ve_don_kem_anh(self):
        d = self.d
        self.client.force_login(d.khach)
        url_don = reverse("tro_chuyen:khach_tu_don_hang", args=[self.don.pk])
        self.assertContains(self.client.get(url_don), self.don.ma_don_hang)
        self.assertFalse(CuocTroChuyen.objects.exists())
        tu_don = self.client.post(url_don, {"noi_dung": "", "cac_anh": [anh_png()]})
        phong = CuocTroChuyen.objects.get()
        self.assertRedirects(tu_don, reverse("tro_chuyen:khach_chi_tiet", args=[phong.pk]))
        tin = TinNhan.objects.get()
        self.assertEqual((tin.don_hang, tin.so_anh), (self.don, 1))
        anh = tin.cac_anh.get()
        url_anh = reverse("tro_chuyen:khach_anh", args=[anh.pk])
        self.assertEqual(self.client.get(url_anh)["Content-Type"], "image/webp")
        # Tin kèm ảnh trong cuộc đang mở (HTTP); gửi lại cùng mã không nhân đôi.
        url_gui = reverse("tro_chuyen:khach_gui_tin", args=[phong.pk])
        ma = str(uuid4())
        for _ in range(2):
            ok = self.client.post(
                url_gui, {"ma_tin_nhan": ma, "noi_dung": "Ảnh hộp thuốc", "cac_anh": [anh_png()]}
            )
            self.assertEqual(ok.status_code, 200)
        self.assertEqual(TinNhan.objects.count(), 2)
        self.assertEqual(ok.json()["tin"]["noi_dung"], "Ảnh hộp thuốc")
        loi = self.client.post(url_gui, {"ma_tin_nhan": str(uuid4()), "noi_dung": ""})
        self.assertEqual(loi.json()["loi"], "Hãy nhập nội dung tin nhắn hoặc chọn ảnh.")
        # Người ngoài cuộc không xem được ảnh; nhân sự chi nhánh xem được qua khu quản lý.
        url_anh_noi_bo = reverse("tro_chuyen:anh", args=[anh.pk])
        self.client.force_login(d.khac)
        self.assertEqual(self.client.get(url_anh).status_code, 404)
        self.client.force_login(d.ql2)
        self.assertEqual(self.client.get(url_anh_noi_bo).status_code, 404)
        self.client.force_login(d.nv)
        self.assertEqual(self.client.get(url_anh_noi_bo).status_code, 200)

    def test_nut_tu_van_noi_va_huy_hieu(self):
        trang = self.client.get(reverse("chung:trang_chu"))
        self.assertContains(trang, "nut-tu-van-noi")
        self.assertContains(trang, "ly_do=tu_van")
        phong = mo_phong(self.d.khach, self.d.cn)
        ghi_tin_nhan(self.d.nv, phong, str(uuid4()), "Chào bạn")
        self.client.force_login(self.d.khach)
        trang = self.client.get(reverse("chung:trang_chu"))
        self.assertContains(trang, "data-khung-tu-van")
        self.assertEqual(trang.context["so_tin_chua_doc"], 1)
        self.assertEqual(self.client.get(reverse("tro_chuyen:so_chua_doc")).json(), {"tong": 1})
        san_pham = self.client.get(
            reverse("danh_muc:khach_thuoc_chi_tiet", args=[self.d.thuoc.ma_thuoc])
        )
        self.assertContains(san_pham, "Hỏi dược sĩ về thuốc này")
        self.client.logout()
        self.assertContains(
            self.client.get(reverse("tai_khoan:dang_nhap") + "?ly_do=tu_van"),
            "Đăng nhập để nhắn tin với dược sĩ",
        )

    def test_nhan_su_hop_thu_loc_va_mo_tu_don(self):
        d = self.d
        url_don = reverse("tro_chuyen:tu_don_hang", args=[self.don.pk])
        self.client.force_login(d.nv)
        # Khách chưa từng nhắn: trang soạn không tạo cuộc trò chuyện, gửi rồi mới có.
        self.assertContains(self.client.get(url_don), "Gửi tin nhắn")
        self.assertFalse(CuocTroChuyen.objects.exists())
        mo = self.client.post(url_don, {"noi_dung": "Đơn đã soạn xong ạ"})
        phong = CuocTroChuyen.objects.get()
        url_phong = reverse("tro_chuyen:chi_tiet", args=[phong.pk])
        self.assertRedirects(mo, url_phong)
        self.assertEqual(TinNhan.objects.get().don_hang, self.don)
        ghi_tin_nhan(d.khach, phong, str(uuid4()), "Hỏi thuốc ho")
        url = reverse("tro_chuyen:danh_sach")
        hop_thu = self.client.get(url)
        self.assertEqual(
            dict((ma, so) for ma, _, so in hop_thu.context["cac_the"])["cho_tra_loi"], 1
        )
        self.assertContains(hop_thu, "Chờ ")
        menu = {m["ten"]: m for m in hop_thu.context["menu_ung_dung"]}
        self.assertEqual(menu["tro_chuyen:danh_sach"]["so"], 1)
        self.assertEqual(len(self.client.get(url, {"tim": "thuốc ho"}).context["trang"]), 1)
        tim_don = self.client.get(url, {"tim": self.don.ma_don_hang})
        self.assertEqual(len(tim_don.context["trang"]), 1)
        self.assertEqual(len(self.client.get(url, {"tim": "không khớp"}).context["trang"]), 0)
        self.assertEqual(list(self.client.get(url_phong).context["don_da_hoi"]), [self.don])
        # Đã xong: rời hàng chờ, quay lại đúng bộ lọc đang xem.
        xong = self.client.post(
            reverse("tro_chuyen:xong", args=[phong.pk]), {"quay_lai": url + "?tim=ho"}
        )
        self.assertRedirects(xong, url + "?tim=ho")
        self.assertEqual(len(self.client.get(url).context["trang"]), 0)
        self.assertEqual(len(self.client.get(url, {"trang_thai": "da_xong"}).context["trang"]), 1)
        # Đã có cuộc trò chuyện: nút ở trang đơn mở cuộc đó kèm thẻ đơn chờ gửi.
        self.assertRedirects(self.client.get(url_don), url_phong + f"?don={self.don.pk}")
        cho = self.client.get(url_phong, {"don": self.don.pk})
        self.assertEqual(cho.context["the_cho"]["id"], self.don.pk)
        self.assertContains(
            self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[self.don.pk])),
            "Nhắn khách về đơn này",
        )


@override_settings(CHANNEL_LAYERS=KENH_BO_NHO)
class ThoiGianThucTests(TransactionTestCase):
    def setUp(self):
        self.d = tao_du_lieu()
        self.phong = mo_phong(self.d.khach, self.d.cn)

    def cong(self, duong_dan, nguoi):
        cong = WebsocketCommunicator(URLRouter(websocket_urlpatterns), duong_dan)
        cong.scope["user"] = nguoi
        return cong

    async def test_tin_moi_bao_nha_thuoc_va_da_xem_bao_khach(self):
        thong_bao_nv = self.cong("/ws/thong-bao/", self.d.nv)
        thong_bao_khac = self.cong("/ws/thong-bao/", self.d.ql2)
        khach = self.cong(f"/ws/tro-chuyen/{self.phong.pk}/", self.d.khach)
        nhan_vien = self.cong(f"/ws/tro-chuyen/{self.phong.pk}/", self.d.nv)
        for cong in (thong_bao_nv, thong_bao_khac, khach, nhan_vien):
            self.assertTrue((await cong.connect())[0])
        try:
            self.assertEqual(
                await thong_bao_nv.receive_json_from(), {"loai": "so_chua_doc", "tong": 0}
            )
            await thong_bao_khac.receive_json_from()
            await khach.receive_json_from()
            await nhan_vien.receive_json_from()
            await khach.send_json_to(
                {
                    "ma_tin_nhan": str(uuid4()),
                    "noi_dung": "Còn hàng không?",
                    "thuoc": self.d.thuoc.pk,
                }
            )
            self.assertEqual((await khach.receive_json_from())["loai"], "da_luu")
            bao = await thong_bao_nv.receive_json_from()
            self.assertEqual(
                (bao["loai"], bao["tong"], bao["ma_phong"]), ("tin_moi", 1, self.phong.pk)
            )
            # Chi nhánh khác không nhận thông báo của chi nhánh này.
            self.assertTrue(await thong_bao_khac.receive_nothing(timeout=0.2))
            tin = (await nhan_vien.receive_json_from())["tin"]
            self.assertEqual(tin["the"]["ten"], self.d.thuoc.ten_thuoc)
            await khach.receive_json_from()
            await nhan_vien.send_json_to({"loai": "da_doc", "id_tin": tin["id_tin_nhan"]})
            self.assertEqual(
                await khach.receive_json_from(),
                {"loai": "da_doc", "ben": "nha_thuoc", "id_tin": tin["id_tin_nhan"]},
            )
            self.assertEqual(
                await thong_bao_nv.receive_json_from(), {"loai": "so_chua_doc", "tong": 0}
            )
            self.assertEqual(await database_sync_to_async(dem_chua_doc)(self.d.nv), 0)
            # Thẻ đính kèm sai được báo lỗi tiếng Việt, không làm rớt kết nối.
            await khach.send_json_to(
                {"ma_tin_nhan": str(uuid4()), "noi_dung": "Thẻ lạ", "don_hang": "abc"}
            )
            self.assertEqual(
                await khach.receive_json_from(),
                {"loai": "loi", "thong_bao": "Thẻ đính kèm không hợp lệ."},
            )
        finally:
            for cong in (thong_bao_nv, thong_bao_khac, khach, nhan_vien):
                await cong.disconnect()

    async def test_vang_lai_khong_vao_kenh_thong_bao(self):
        from django.contrib.auth.models import AnonymousUser

        cong = self.cong("/ws/thong-bao/", AnonymousUser())
        ket_noi, ma = await cong.connect()
        self.assertFalse(ket_noi)
        self.assertEqual(ma, 4403)

    async def test_tin_kem_anh_gui_qua_http_van_phat_toi_phong(self):
        nhan_vien = self.cong(f"/ws/tro-chuyen/{self.phong.pk}/", self.d.nv)
        thong_bao_nv = self.cong("/ws/thong-bao/", self.d.nv)
        self.assertTrue((await nhan_vien.connect())[0])
        self.assertTrue((await thong_bao_nv.connect())[0])
        try:
            await nhan_vien.receive_json_from()
            await thong_bao_nv.receive_json_from()

            def gui_anh():
                # Cuộc trò chuyện chỉ hiện với khách sau khi đã có tin.
                ghi_tin_nhan(self.d.nv, self.phong, str(uuid4()), "Chào anh/chị")
                self.client.force_login(self.d.khach)
                return self.client.post(
                    reverse("tro_chuyen:khach_gui_tin", args=[self.phong.pk]),
                    {"ma_tin_nhan": str(uuid4()), "noi_dung": "", "cac_anh": [anh_png()]},
                )

            phan_hoi = await database_sync_to_async(gui_anh)()
            self.assertEqual(phan_hoi.status_code, 200)
            tin = (await nhan_vien.receive_json_from())["tin"]
            self.assertEqual(len(tin["anh"]), 1)
            bao = await thong_bao_nv.receive_json_from()
            self.assertEqual(bao["xem_truoc"], "Đã gửi ảnh")
        finally:
            await nhan_vien.disconnect()
            await thong_bao_nv.disconnect()

    async def test_cau_hoi_dau_gui_qua_form_van_bao_nha_thuoc(self):
        thong_bao_nv = self.cong("/ws/thong-bao/", self.d.nv)
        self.assertTrue((await thong_bao_nv.connect())[0])
        try:
            await thong_bao_nv.receive_json_from()

            def gui_form():
                self.client.force_login(self.d.khach)
                return self.client.post(
                    reverse("tro_chuyen:khach_danh_sach"),
                    {"chi_nhanh": self.d.cn.pk, "noi_dung": "Cho em hỏi thuốc dị ứng"},
                )

            phan_hoi = await database_sync_to_async(gui_form)()
            self.assertEqual(phan_hoi.status_code, 302)
            bao = await thong_bao_nv.receive_json_from()
            self.assertEqual(
                (bao["loai"], bao["xem_truoc"], bao["tong"]),
                ("tin_moi", "Cho em hỏi thuốc dị ứng", 1),
            )
        finally:
            await thong_bao_nv.disconnect()
