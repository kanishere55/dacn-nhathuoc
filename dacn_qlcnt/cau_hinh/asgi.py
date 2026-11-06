import os

from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cau_hinh.settings")

from ung_dung.chung.tai_len import GioiHanNoiDungHTTP

# Giới hạn HTTP trước khi Django đọc body; tuyến WebSocket được cấu hình riêng.
application = ProtocolTypeRouter({"http": GioiHanNoiDungHTTP(get_asgi_application())})
