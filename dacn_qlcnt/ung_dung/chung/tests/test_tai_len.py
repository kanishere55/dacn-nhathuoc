from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.uploadhandler import StopFutureHandlers
from django.http import HttpResponse
from django.test import SimpleTestCase, override_settings
from django.urls import path

from ung_dung.chung.tai_len import GioiHanNoiDungHTTP, LoiTaiLenQuaLon, TaiLenTrongBoNho


def nhan_tep_thu(request):
    tep = request.FILES["tep"]
    return HttpResponse(f"{tep.size}:{isinstance(tep.file, BytesIO)}")


urlpatterns = [path("nhan-tep/", nhan_tep_thu)]


@override_settings(
    ROOT_URLCONF=__name__, FILE_UPLOAD_MAX_MEMORY_SIZE=1024, DATA_UPLOAD_MAX_MEMORY_SIZE=1024
)
class TaiLenTests(SimpleTestCase):
    def test_tep_nho_duoc_nhan_trong_ram(self):
        phan_hoi = self.client.post("/nhan-tep/", {"tep": SimpleUploadedFile("thu.txt", b"abc")})
        self.assertEqual(phan_hoi.status_code, 200)
        self.assertEqual(phan_hoi.content, b"3:True")

    def test_tep_qua_lon_tra_413_ro_rang_thay_vi_files_rong(self):
        for debug in (True, False):
            with self.subTest(debug=debug), override_settings(DEBUG=debug):
                phan_hoi = self.client.post(
                    "/nhan-tep/", {"tep": SimpleUploadedFile("thu.txt", b"a" * 2048)}
                )
                self.assertContains(phan_hoi, "vượt giới hạn", status_code=413)

    def test_nhieu_tep_khong_lach_gioi_han_tong(self):
        phan_hoi = self.client.post(
            "/nhan-tep/",
            {
                "tep": [
                    SimpleUploadedFile("a.txt", b"a" * 700),
                    SimpleUploadedFile("b.txt", b"b" * 700),
                ]
            },
        )
        self.assertEqual(phan_hoi.status_code, 413)

    def test_dem_chunk_thuc_te_khi_khong_co_content_length(self):
        bo_nhan = TaiLenTrongBoNho()
        bo_nhan.handle_raw_input(None, {}, None, b"ranh-gioi")
        with self.assertRaises(StopFutureHandlers):
            bo_nhan.new_file("tep", "thu.txt", "text/plain", None)
        self.addCleanup(bo_nhan.file.close)
        bo_nhan.receive_data_chunk(b"a" * 512, 0)
        bo_nhan.receive_data_chunk(b"b" * 512, 512)
        self.assertIsInstance(bo_nhan.file, BytesIO)
        with self.assertRaises(LoiTaiLenQuaLon):
            bo_nhan.receive_data_chunk(b"c", 1024)

    async def test_asgi_chan_truoc_khi_body_duoc_spool_ra_dia(self):
        da_nhan = []
        da_gui = []

        async def ung_dung(scope, receive, send):
            su_kien = await receive()
            da_nhan.append(su_kien)

        async def receive():
            return {"type": "http.request", "body": b"a" * 2048, "more_body": False}

        async def send(su_kien):
            da_gui.append(su_kien)

        await GioiHanNoiDungHTTP(ung_dung)({"type": "http"}, receive, send)
        self.assertEqual(da_nhan, [])
        self.assertEqual(da_gui[0]["status"], 413)
        self.assertIn("vượt giới hạn", da_gui[1]["body"].decode())
