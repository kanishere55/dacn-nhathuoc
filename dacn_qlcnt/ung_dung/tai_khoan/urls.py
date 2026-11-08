from django.urls import path

from .views import khach, noi_bo

app_name = "tai_khoan"
urlpatterns = [
    path("tai-khoan/dang-nhap/", khach.dang_nhap, name="dang_nhap"),
    path("tai-khoan/dang-xuat/", khach.dang_xuat, name="dang_xuat"),
    path("tai-khoan/dang-ky/", khach.dang_ky, name="dang_ky"),
    path("tai-khoan-cua-toi/", khach.cua_toi, name="cua_toi"),
    path("quan-ly/tai-khoan/", noi_bo.danh_sach, name="danh_sach"),
    path("quan-ly/tai-khoan/tao/", noi_bo.chinh_sua, name="tao"),
    path("quan-ly/tai-khoan/<int:ma>/sua/", noi_bo.chinh_sua, name="sua"),
]
