from django.urls import path

from .consumers import ThongBaoConsumer, TroChuyenConsumer

websocket_urlpatterns = [
    path("ws/tro-chuyen/<int:ma>/", TroChuyenConsumer.as_asgi()),
    path("ws/thong-bao/", ThongBaoConsumer.as_asgi()),
]
