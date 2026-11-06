import os

from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cau_hinh.settings")

# Chưa mở WebSocket khi đặc tả phòng chat và quyền truy cập chưa được duyệt.
application = ProtocolTypeRouter({"http": get_asgi_application()})
