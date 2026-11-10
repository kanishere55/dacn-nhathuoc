from django.urls import path

from . import api, views

app_name = "du_bao"
urlpatterns = [
    path("", views.ket_qua, name="ket_qua"),
    path("api/nhom/<str:ma_atc>/", api.chi_tiet_nhom, name="chi_tiet_nhom"),
]
