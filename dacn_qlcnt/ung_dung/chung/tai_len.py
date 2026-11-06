from django.conf import settings
from django.core.files.uploadhandler import MemoryFileUploadHandler
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


class LoiTaiLenQuaLon(Exception):
    pass


def thong_bao_gioi_han():
    return (
        f"Yêu cầu tải lên vượt giới hạn {settings.FILE_UPLOAD_MAX_MEMORY_SIZE} byte. "
        "Hãy chọn tệp nhỏ hơn; dữ liệu dự báo lớn được nạp bằng lệnh quản lý."
    )


class TaiLenTrongBoNho(MemoryFileUploadHandler):
    def handle_raw_input(self, input_data, META, content_length, boundary, encoding=None):
        if content_length is not None and content_length > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
            raise LoiTaiLenQuaLon
        # Không có handler ghi đĩa dự phòng; thiếu Content-Length vẫn kiểm từng chunk.
        self.activated = True
        self.so_byte_da_nhan = 0

    def receive_data_chunk(self, raw_data, start):
        self.so_byte_da_nhan += len(raw_data)
        if self.so_byte_da_nhan > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
            raise LoiTaiLenQuaLon
        return super().receive_data_chunk(raw_data, start)


class KiemTraTaiLen(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.content_type == "multipart/form-data":
            try:
                # Phân tích trước CSRF để luôn trả lỗi tiếng Việt thay vì FILES rỗng.
                _ = request.POST
            except LoiTaiLenQuaLon:
                return HttpResponse(thong_bao_gioi_han(), status=413)
        return None


class GioiHanNoiDungHTTP:
    def __init__(self, ung_dung):
        self.ung_dung = ung_dung

    async def __call__(self, scope, receive, send):
        so_byte = 0

        async def nhan_co_gioi_han():
            nonlocal so_byte
            su_kien = await receive()
            if su_kien["type"] == "http.request":
                so_byte += len(su_kien.get("body", b""))
                if so_byte > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
                    raise LoiTaiLenQuaLon
            return su_kien

        try:
            # Chặn trước khi Django ASGI có thể chuyển SpooledTemporaryFile xuống đĩa.
            await self.ung_dung(scope, nhan_co_gioi_han, send)
        except LoiTaiLenQuaLon:
            await send(
                {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                }
            )
            await send({"type": "http.response.body", "body": thong_bao_gioi_han().encode()})
