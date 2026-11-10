"""WebSocket trò chuyện qua Redis. Tin và mốc đã đọc ghi PostgreSQL trước, Redis chỉ chuyển tín hiệu."""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError

from ung_dung.chung.permissions import co_quyen, thay_toan_chuoi

from .models import CuocTroChuyen
from .permissions import kiem_tra_phong
from .phat_tin_hieu import (
    NHOM_TOAN_CHUOI,
    nhom_chi_nhanh,
    nhom_khach,
    nhom_nha_thuoc,
    thong_bao_tin_moi,
)
from .selectors import bieu_dien_tin, dem_chua_doc, lay_lich_su
from .services import danh_dau_da_doc, ghi_tin_nhan
from .the_dinh_kem import doc_the


class TroChuyenConsumer(AsyncJsonWebsocketConsumer):
    def lay_doi_tuong(self):
        nguoi = get_user_model().objects.filter(pk=self.scope["user"].pk).first()
        phong = (
            CuocTroChuyen.objects.select_related("chi_nhanh", "khach_hang")
            .filter(pk=self.ma_phong)
            .first()
        )
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
    def luu_tin(self, ma, noi_dung, id_thuoc, id_don):
        nguoi, phong = self.lay_doi_tuong()
        thuoc, don = doc_the(id_thuoc, id_don)
        tin, da_tao = ghi_tin_nhan(nguoi, phong, ma, noi_dung, thuoc=thuoc, don=don)
        thong_bao, nhom = thong_bao_tin_moi(nguoi, phong, tin)
        return bieu_dien_tin(tin, phong.khach_hang_id), da_tao, thong_bao, nhom

    @database_sync_to_async
    def luu_da_doc(self, id_tin):
        nguoi, phong = self.lay_doi_tuong()
        ket_qua = danh_dau_da_doc(nguoi, phong, id_tin)
        if ket_qua is None:
            return None, []
        ben, _ = ket_qua
        nhom = (
            nhom_nha_thuoc(phong.chi_nhanh_id)
            if ben == "nha_thuoc"
            else [nhom_khach(phong.khach_hang_id)]
        )
        return ket_qua, nhom

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
            await self.send_json({"loai": "lich_su", **await self.lich_su()})
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
            if content.get("loai") == "da_doc":
                await self.xu_ly_da_doc(content.get("id_tin"))
                return
            tin, da_tao, thong_bao, nhom = await self.luu_tin(
                content.get("ma_tin_nhan"),
                content.get("noi_dung"),
                content.get("thuoc"),
                content.get("don_hang"),
            )
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
            for ten_nhom in nhom:
                await self.channel_layer.group_send(
                    ten_nhom, {"type": "tin_moi", "thong_bao": thong_bao}
                )

    async def xu_ly_da_doc(self, id_tin):
        ket_qua, nhom = await self.luu_da_doc(id_tin)
        if ket_qua is None:
            return
        ben, id_moi = ket_qua
        await self.channel_layer.group_send(
            self.nhom, {"type": "phat_da_doc", "ben": ben, "id_tin": id_moi}
        )
        # Các tab khác của cùng phía cập nhật lại huy hiệu chưa đọc.
        for ten_nhom in nhom:
            await self.channel_layer.group_send(ten_nhom, {"type": "dem_lai"})

    async def phat_tin(self, su_kien):
        try:
            await self.kiem_quyen()
        except PermissionDenied:
            await self.close(code=4403)
            return
        await self.send_json({"loai": "tin_nhan", "tin": su_kien["tin"]})

    async def phat_da_doc(self, su_kien):
        await self.send_json({"loai": "da_doc", "ben": su_kien["ben"], "id_tin": su_kien["id_tin"]})


class ThongBaoConsumer(AsyncJsonWebsocketConsumer):
    """Kênh thông báo của từng người: tin mới tới mình và số tin chưa đọc."""

    @database_sync_to_async
    def cac_nhom(self):
        nguoi = get_user_model().objects.filter(pk=self.scope["user"].pk).first()
        if nguoi is None or not nguoi.is_active:
            return None
        self.nguoi = nguoi
        if nguoi.vai_tro == "khach_hang":
            return [nhom_khach(nguoi.pk)]
        if not co_quyen(nguoi, "tro_chuyen.dung"):
            return None
        if thay_toan_chuoi(nguoi):
            return [NHOM_TOAN_CHUOI]
        return [nhom_chi_nhanh(nguoi.chi_nhanh_id)] if nguoi.chi_nhanh_id else None

    @database_sync_to_async
    def tong_chua_doc(self):
        return dem_chua_doc(self.nguoi)

    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close(code=4403)
            return
        nhom = await self.cac_nhom()
        if not nhom:
            await self.close(code=4403)
            return
        self.cac_nhom_da_vao = nhom
        for ten_nhom in nhom:
            await self.channel_layer.group_add(ten_nhom, self.channel_name)
        await self.accept()
        await self.send_json({"loai": "so_chua_doc", "tong": await self.tong_chua_doc()})

    async def disconnect(self, close_code):
        for ten_nhom in getattr(self, "cac_nhom_da_vao", []):
            await self.channel_layer.group_discard(ten_nhom, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if isinstance(content, dict) and content.get("loai") == "kiem_tra_ket_noi":
            await self.send_json({"loai": "so_chua_doc", "tong": await self.tong_chua_doc()})

    async def tin_moi(self, su_kien):
        await self.send_json(
            {"loai": "tin_moi", **su_kien["thong_bao"], "tong": await self.tong_chua_doc()}
        )

    async def dem_lai(self, su_kien):
        await self.send_json({"loai": "so_chua_doc", "tong": await self.tong_chua_doc()})
