from django.urls import path

from .views import khach, noi_bo

app_name = "tro_chuyen"
urlpatterns = [
    path("tro-chuyen/", khach.danh_sach, name="khach_danh_sach"),
    path("tro-chuyen/<int:ma>/", khach.chi_tiet, name="khach_chi_tiet"),
    path("quan-ly/tro-chuyen/", noi_bo.danh_sach, name="danh_sach"),
    path("quan-ly/tro-chuyen/<int:ma>/", noi_bo.chi_tiet, name="chi_tiet"),
]
