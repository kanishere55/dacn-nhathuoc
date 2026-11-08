import os
from uuid import uuid4

from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from django.urls import reverse

from ung_dung.kho.tests.du_lieu import tao_du_lieu

from ..models import TinNhan
from ..routing import websocket_urlpatterns
from ..services import ghi_tin_nhan, mo_phong

# Mặc định test không phụ thuộc dịch vụ ngoài. Runner Redis cung cấp URL riêng.
MAY_CHU_REDIS_TEST = os.environ.get("DACN_TEST_REDIS_URL")
KENH_THU = (
    {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [MAY_CHU_REDIS_TEST]},
        }
    }
    if MAY_CHU_REDIS_TEST
    else {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)


@override_settings(CHANNEL_LAYERS=KENH_THU)
class TroChuyenTests(TransactionTestCase):
    def setUp(self):
        self.d = tao_du_lieu()
        self.phong = mo_phong(self.d.khach, self.d.cn)

    def test_khach_chi_doc_duoc_phong_cua_minh(self):
        self.client.force_login(self.d.khac)
        self.assertEqual(
            self.client.get(reverse("tro_chuyen:chi_tiet", args=[self.phong.pk])).status_code, 404
        )
        self.assertNotContains(self.client.get(reverse("tro_chuyen:danh_sach")), str(self.d.khach))
        self.client.force_login(self.d.khach)
        self.assertContains(
            self.client.get(reverse("tro_chuyen:chi_tiet", args=[self.phong.pk])), "Tin nhắn"
        )

    def ket_noi(self, nguoi):
        cong = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns), f"/ws/tro-chuyen/{self.phong.pk}/"
        )
        cong.scope["user"] = nguoi
        return cong

    async def test_socket_tu_choi_khach_khac(self):
        cong = self.ket_noi(self.d.khac)
        ket_noi, ma_loi = await cong.connect()
        self.assertFalse(ket_noi)
        self.assertEqual(ma_loi, 4403)
        await cong.disconnect()

    async def test_luu_db_truoc_phat_va_gui_lai_khong_nhan_doi(self):
        khach = self.ket_noi(self.d.khach)
        nhan_vien = self.ket_noi(self.d.nv)
        self.assertTrue((await khach.connect())[0])
        self.assertTrue((await nhan_vien.connect())[0])
        try:
            self.assertEqual((await khach.receive_json_from())["loai"], "lich_su")
            self.assertEqual((await nhan_vien.receive_json_from())["loai"], "lich_su")
            du_lieu = {"ma_tin_nhan": str(uuid4()), "noi_dung": "Chào nhà thuốc"}
            await khach.send_json_to(du_lieu)
            self.assertEqual((await khach.receive_json_from())["loai"], "da_luu")
            self.assertEqual((await khach.receive_json_from())["loai"], "tin_nhan")
            tin = (await nhan_vien.receive_json_from())["tin"]
            da_luu = await database_sync_to_async(TinNhan.objects.get)(pk=tin["id_tin_nhan"])
            self.assertEqual(da_luu.noi_dung_tin_nhan, du_lieu["noi_dung"])
            await khach.send_json_to(du_lieu)
            self.assertEqual((await khach.receive_json_from())["loai"], "da_luu")
            self.assertEqual(await database_sync_to_async(TinNhan.objects.count)(), 1)
        finally:
            await khach.disconnect()
            await nhan_vien.disconnect()

    async def test_kiem_tra_ket_noi_va_lay_tin_da_luu_sau_khi_noi_lai(self):
        khach = self.ket_noi(self.d.khach)
        self.assertTrue((await khach.connect())[0])
        try:
            self.assertEqual(await khach.receive_json_from(), {"loai": "lich_su", "cac_tin": []})
            await khach.send_json_to({"loai": "kiem_tra_ket_noi"})
            self.assertEqual(await khach.receive_json_from(), {"loai": "ket_noi_con_song"})
            self.assertEqual(await TinNhan.objects.acount(), 0)
        finally:
            await khach.disconnect()

        tin, _ = await database_sync_to_async(ghi_tin_nhan)(
            self.d.nv, self.phong, str(uuid4()), "Tin lưu lúc khách mất mạng"
        )
        khach = self.ket_noi(self.d.khach)
        self.assertTrue((await khach.connect())[0])
        try:
            lich_su = await khach.receive_json_from()
            self.assertEqual(lich_su["loai"], "lich_su")
            self.assertEqual([muc["id_tin_nhan"] for muc in lich_su["cac_tin"]], [tin.pk])
            await get_user_model().objects.filter(pk=self.d.khach.pk).aupdate(dang_hoat_dong=False)
            await khach.send_json_to({"loai": "kiem_tra_ket_noi"})
            self.assertEqual(
                await khach.receive_output(), {"type": "websocket.close", "code": 4403}
            )
        finally:
            await khach.disconnect()
