"""Phòng tư vấn / phòng theo đơn, mốc đã đọc, số chưa đọc, thông báo thời gian thực, nút tư vấn nổi."""

from uuid import uuid4

from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from ung_dung.ban_hang.services.dat_hang import dat_hang
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton

from ..models import CuocTroChuyen, TinNhan
from ..routing import websocket_urlpatterns
from ..selectors import dem_chua_doc, lay_hop_thu, lay_tin_cu
from ..services import (
    GIOI_HAN_TIN_MOT_PHUT,
    bat_dau_tu_van,
    bat_dau_ve_don,
    danh_dau_da_doc,
    danh_dau_xong,
    ghi_tin_nhan,
    mo_phong,
    mo_phong_don_hang,
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


class NghiepVuTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        cls.don = tao_don(cls.d)

    def test_phong_tu_van_duy_nhat_va_phong_don_tach_rieng(self):
        d = self.d
        tu_van = mo_phong(d.khach, d.cn)
        self.assertEqual(mo_phong(d.khach, d.cn), tu_van)
        theo_don = mo_phong_don_hang(d.khach, self.don)
        self.assertNotEqual(theo_don, tu_van)
        self.assertEqual(theo_don.loai_cuoc_tro_chuyen, "don_hang")
        self.assertEqual(theo_don.chi_nhanh_id, self.don.chi_nhanh_id)
        # Nhân sự chi nhánh mở lại đúng phòng của đơn, không tạo phòng thứ hai.
        self.assertEqual(mo_phong_don_hang(d.nv, self.don), theo_don)
        with self.assertRaises(PermissionDenied):
            mo_phong_don_hang(d.khac, self.don)
        with self.assertRaises(PermissionDenied):
            mo_phong_don_hang(d.ql2, self.don)

    def test_rang_buoc_csdl_loai_khop_don(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            CuocTroChuyen.objects.create(
                khach_hang=self.d.khach, chi_nhanh=self.d.cn, loai_cuoc_tro_chuyen="don_hang"
            )
        mo_phong(self.d.khach, self.d.cn)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CuocTroChuyen.objects.create(khach_hang=self.d.khach, chi_nhanh=self.d.cn)

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
        # Mốc không lùi và không trỏ sang tin của phòng khác.
        danh_dau_da_doc(d.khach, phong, tra_loi.pk)
        self.assertIsNone(danh_dau_da_doc(d.khach, phong, tin_khach.pk))
        phong_don = mo_phong_don_hang(d.khach, self.don)
        tin_khac, _ = ghi_tin_nhan(d.khach, phong_don, str(uuid4()), "Đơn của em")
        with self.assertRaises(ValidationError):
            danh_dau_da_doc(d.khach, phong, tin_khac.pk)
        self.assertEqual(lay_hop_thu(d.nv).filter(loai_cuoc_tro_chuyen="don_hang").get(), phong_don)
        self.assertEqual(lay_hop_thu(d.nv, "da_tra_loi").get(), phong)
        # Nhân sự chi nhánh khác không thấy và không đếm tin của chi nhánh này.
        self.assertEqual(dem_chua_doc(d.ql2), 0)


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
        # Nhắn lần nữa dùng lại đúng phòng, không tạo phòng mới.
        self.assertEqual(bat_dau_ve_don(d.nv, self.don, "Chiều nay có ạ"), phong)
        self.assertEqual(CuocTroChuyen.objects.count(), 1)
        with self.assertRaises(PermissionDenied):
            bat_dau_ve_don(d.khac, self.don, "Spam")

    def test_gioi_han_toc_do_chi_ap_cho_khach(self):
        d = self.d
        phong = bat_dau_tu_van(d.khach, d.cn, "Tin 1")
        for i in range(GIOI_HAN_TIN_MOT_PHUT - 1):
            ghi_tin_nhan(d.khach, phong, str(uuid4()), f"Tin {i + 2}")
        with self.assertRaises(ValidationError):
            ghi_tin_nhan(d.khach, phong, str(uuid4()), "Tin quá nhanh")
        for i in range(GIOI_HAN_TIN_MOT_PHUT + 2):
            ghi_tin_nhan(d.nv, phong, str(uuid4()), f"Trả lời {i}")

    def test_da_xong_roi_hang_cho_va_tu_mo_lai(self):
        d = self.d
        phong = bat_dau_tu_van(d.khach, d.cn, "Hỏi thuốc ho")
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
        phong = bat_dau_tu_van(d.khach, d.cn, "Tin đầu")
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

    def test_khach_hoi_duoc_si_va_mo_phong_tu_don(self):
        d = self.d
        self.client.force_login(d.khach)
        url = reverse("tro_chuyen:khach_danh_sach")
        trang = self.client.get(url)
        self.assertContains(trang, "Hỏi dược sĩ")
        self.assertEqual(trang.context["form"]["chi_nhanh"].value(), d.cn.pk)
        phan_hoi = self.client.post(
            url, {"chi_nhanh": d.cn.pk, "noi_dung": "Bé 5 tuổi sốt dùng gì?", "nhung": "1"}
        )
        phong = CuocTroChuyen.objects.get(loai_cuoc_tro_chuyen="tu_van")
        self.assertRedirects(
            phan_hoi, reverse("tro_chuyen:khach_chi_tiet", args=[phong.pk]) + "?nhung=1"
        )
        self.assertEqual(TinNhan.objects.get().noi_dung_tin_nhan, "Bé 5 tuổi sốt dùng gì?")
        nhung = self.client.get(reverse("tro_chuyen:khach_chi_tiet", args=[phong.pk]) + "?nhung=1")
        self.assertEqual(nhung["X-Frame-Options"], "SAMEORIGIN")
        self.assertNotContains(nhung, "chan-trang-khach")
        # Câu hỏi trống không tạo phòng.
        self.client.post(url, {"chi_nhanh": d.cn.pk, "noi_dung": ""})
        self.assertEqual(CuocTroChuyen.objects.count(), 1)
        # Mở trang soạn tin về đơn không tạo gì; chỉ khi gửi mới có phòng.
        url_don = reverse("tro_chuyen:khach_tu_don_hang", args=[self.don.pk])
        soan = self.client.get(url_don)
        self.assertContains(soan, self.don.ma_don_hang)
        self.assertFalse(CuocTroChuyen.objects.filter(don_hang=self.don).exists())
        tu_don = self.client.post(url_don, {"noi_dung": "Khi nào nhận được hàng?"})
        phong_don = CuocTroChuyen.objects.get(don_hang=self.don)
        self.assertRedirects(tu_don, reverse("tro_chuyen:khach_chi_tiet", args=[phong_don.pk]))
        self.assertRedirects(
            self.client.get(url_don), reverse("tro_chuyen:khach_chi_tiet", args=[phong_don.pk])
        )
        self.client.force_login(d.khac)
        self.assertEqual(
            self.client.post(
                reverse("tro_chuyen:khach_tu_don_hang", args=[self.don.pk])
            ).status_code,
            404,
        )

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
        self.client.logout()
        self.assertContains(
            self.client.get(reverse("tai_khoan:dang_nhap") + "?ly_do=tu_van"),
            "Đăng nhập để nhắn tin với dược sĩ",
        )

    def test_nhan_su_hop_thu_loc_va_mo_tu_don(self):
        d = self.d
        phong = mo_phong(d.khach, d.cn)
        ghi_tin_nhan(d.khach, phong, str(uuid4()), "Hỏi thuốc ho")
        self.client.force_login(d.nv)
        hop_thu = self.client.get(reverse("tro_chuyen:danh_sach"))
        self.assertEqual(
            dict((ma, so) for ma, _, so in hop_thu.context["cac_the"])["cho_tra_loi"], 1
        )
        self.assertContains(hop_thu, "Chờ ")
        self.assertContains(hop_thu, "Tư vấn")
        menu = {m["ten"]: m for m in hop_thu.context["menu_ung_dung"]}
        self.assertEqual(menu["tro_chuyen:danh_sach"]["so"], 1)
        url = reverse("tro_chuyen:danh_sach")
        self.assertEqual(len(self.client.get(url, {"loai": "don_hang"}).context["trang"]), 0)
        self.assertEqual(len(self.client.get(url, {"tim": "thuốc ho"}).context["trang"]), 1)
        self.assertEqual(len(self.client.get(url, {"tim": "không khớp"}).context["trang"]), 0)
        # Đã xong: rời hàng chờ, quay lại đúng thẻ đang xem.
        xong = self.client.post(
            reverse("tro_chuyen:xong", args=[phong.pk]), {"quay_lai": url + "?loai=tu_van"}
        )
        self.assertRedirects(xong, url + "?loai=tu_van")
        self.assertEqual(len(self.client.get(url).context["trang"]), 0)
        self.assertEqual(len(self.client.get(url, {"trang_thai": "da_xong"}).context["trang"]), 1)
        # Nhân sự soạn tin về đơn: trang soạn không tạo phòng, gửi rồi mới có.
        url_don = reverse("tro_chuyen:tu_don_hang", args=[self.don.pk])
        self.assertContains(self.client.get(url_don), "Gửi tin nhắn")
        self.assertFalse(CuocTroChuyen.objects.filter(don_hang=self.don).exists())
        mo = self.client.post(url_don, {"noi_dung": "Đơn đã soạn xong ạ"})
        phong_don = CuocTroChuyen.objects.get(don_hang=self.don)
        self.assertRedirects(mo, reverse("tro_chuyen:chi_tiet", args=[phong_don.pk]))
        self.assertContains(
            self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[self.don.pk])),
            "Mở trò chuyện về đơn",
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
            await khach.send_json_to({"ma_tin_nhan": str(uuid4()), "noi_dung": "Còn hàng không?"})
            self.assertEqual((await khach.receive_json_from())["loai"], "da_luu")
            bao = await thong_bao_nv.receive_json_from()
            self.assertEqual(
                (bao["loai"], bao["tong"], bao["ma_phong"]), ("tin_moi", 1, self.phong.pk)
            )
            # Chi nhánh khác không nhận thông báo của chi nhánh này.
            self.assertTrue(await thong_bao_khac.receive_nothing(timeout=0.2))
            tin = (await nhan_vien.receive_json_from())["tin"]
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
        finally:
            for cong in (thong_bao_nv, thong_bao_khac, khach, nhan_vien):
                await cong.disconnect()

    async def test_vang_lai_khong_vao_kenh_thong_bao(self):
        from django.contrib.auth.models import AnonymousUser

        cong = self.cong("/ws/thong-bao/", AnonymousUser())
        ket_noi, ma = await cong.connect()
        self.assertFalse(ket_noi)
        self.assertEqual(ma, 4403)

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
