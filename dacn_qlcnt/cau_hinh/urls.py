from django.urls import include, path

urlpatterns = [
    path("", include("ung_dung.chung.urls")),
    path("tai-khoan/", include("ung_dung.tai_khoan.urls")),
    path("danh-muc/", include("ung_dung.danh_muc.urls")),
    path("kho/", include("ung_dung.kho.urls")),
]
