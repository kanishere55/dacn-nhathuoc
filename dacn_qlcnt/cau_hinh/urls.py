from django.urls import include, path

urlpatterns = [
    path("", include("ung_dung.chung.urls")),
    path("tai-khoan/", include("ung_dung.tai_khoan.urls")),
    path("danh-muc/", include("ung_dung.danh_muc.urls")),
    path("kho/", include("ung_dung.kho.urls")),
    path("ban-hang/", include("ung_dung.ban_hang.urls")),
    path("ban-do/", include("ung_dung.webgis.urls")),
    path("tro-chuyen/", include("ung_dung.tro_chuyen.urls")),
    path("du-bao/", include("ung_dung.du_bao.urls")),
]
