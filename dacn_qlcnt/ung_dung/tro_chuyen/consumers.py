from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError

from .models import CuocTroChuyen
from .permissions import kiem_tra_phong
from .selectors import bieu_dien_tin, lay_lich_su
from .services import ghi_tin_nhan


class TroChuyenConsumer(AsyncJsonWebsocketConsumer):
    def lay_doi_tuong(self):
        nguoi = get_user_model().objects.filter(pk=self.scope["user"].pk).first()
        phong = CuocTroChuyen.objects.filter(pk=self.ma_phong).first()
        if phong is None:
            raise PermissionDenied
        kiem_tra_phong(nguoi, phong)
        return nguoi, phong

    @database_sync_to_async
    def kiem_quyen(self):
        self.lay_doi_tuong()

    @database_sync_to_async
    def lich_su(self):
        return lay_lich_su(*self.lay_doi_tuong())

    @database_sync_to_async
    def luu_tin(self, ma, noi_dung):
        tin, da_tao = ghi_tin_nhan(*self.lay_doi_tuong(), ma, noi_dung)
        return bieu_dien_tin(tin), da_tao

    async def connect(self):
        self.ma_phong = self.scope["url_route"]["kwargs"]["ma"]
        try:
            await self.kiem_quyen()
        except PermissionDenied:
            await self.close(code=4403)
            return
        self.nhom = f"tro_chuyen.{self.ma_phong}"
        await self.channel_layer.group_add(self.nhom, self.channel_name)
        await self.accept()
        try:
            await self.send_json({"loai": "lich_su", "cac_tin": await self.lich_su()})
        except PermissionDenied:
            await self.close(code=4403)

    async def disconnect(self, close_code):
        if hasattr(self, "nhom"):
            await self.channel_layer.group_discard(self.nhom, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        if text_data is None or len(text_data) > 16000:
            await self.send_json(
                {"loai": "loi", "thong_bao": "Tin nhắn quá lớn hoặc sai định dạng."}
            )
            return
        try:
            noi_dung = await self.decode_json(text_data)
        except ValueError:
            await self.send_json({"loai": "loi", "thong_bao": "Tin nhắn sai định dạng."})
            return
        await self.receive_json(noi_dung)

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict):
            await self.send_json({"loai": "loi", "thong_bao": "Tin nhắn sai định dạng."})
            return
        try:
            if content.get("loai") == "kiem_tra_ket_noi":
                await self.kiem_quyen()
                await self.send_json({"loai": "ket_noi_con_song"})
                return
            tin, da_tao = await self.luu_tin(content.get("ma_tin_nhan"), content.get("noi_dung"))
        except PermissionDenied:
            await self.close(code=4403)
            return
        except ValidationError as loi:
            await self.send_json({"loai": "loi", "thong_bao": loi.messages[0]})
            return
        # Hàm đồng bộ đã kết thúc transaction trước khi phát.
        await self.send_json({"loai": "da_luu", "tin": tin, "ma_tin_nhan": content["ma_tin_nhan"]})
        if da_tao:
            await self.channel_layer.group_send(self.nhom, {"type": "phat_tin", "tin": tin})

    async def phat_tin(self, su_kien):
        try:
            await self.kiem_quyen()
        except PermissionDenied:
            await self.close(code=4403)
            return
        await self.send_json({"loai": "tin_nhan", "tin": su_kien["tin"]})
