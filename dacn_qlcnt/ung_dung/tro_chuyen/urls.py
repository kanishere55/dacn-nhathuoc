from django.urls import path

from . import views

app_name = "tro_chuyen"
urlpatterns = [
    path("", views.danh_sach, name="danh_sach"),
    path("<int:ma>/", views.chi_tiet, name="chi_tiet"),
]
