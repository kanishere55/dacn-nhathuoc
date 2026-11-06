from django.urls import path

from . import views

app_name = "tai_khoan"
urlpatterns = [
    path("dang-nhap/", views.dang_nhap, name="dang_nhap"),
    path("dang-xuat/", views.dang_xuat, name="dang_xuat"),
    path("dang-ky/", views.dang_ky, name="dang_ky"),
    path("", views.danh_sach, name="danh_sach"),
    path("tao/", views.chinh_sua, name="tao"),
    path("<int:ma>/sua/", views.chinh_sua, name="sua"),
]
