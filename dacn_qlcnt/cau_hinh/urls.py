from django.urls import include, path

urlpatterns = [
    path("", include("ung_dung.chung.urls")),
    path("danh-muc/", include("ung_dung.danh_muc.urls")),
]
