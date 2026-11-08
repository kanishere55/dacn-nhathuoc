from django.urls import path

from . import views

app_name = "chung"
urlpatterns = [
    path("", views.trang_chu, name="trang_chu"),
    path("quan-ly/", views.bang_dieu_khien, name="bang_dieu_khien"),
]
