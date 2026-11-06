import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cau_hinh.settings")

from ung_dung.chung.tai_len import GioiHanNoiDungHTTP

ung_dung_http = get_asgi_application()

# App registry phải sẵn sàng trước khi tải consumer có dùng model.
from ung_dung.tro_chuyen.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": GioiHanNoiDungHTTP(ung_dung_http),
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
