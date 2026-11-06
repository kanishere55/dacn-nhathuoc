from django.urls import path

from .consumers import TroChuyenConsumer

websocket_urlpatterns = [path("ws/tro-chuyen/<int:ma>/", TroChuyenConsumer.as_asgi())]
