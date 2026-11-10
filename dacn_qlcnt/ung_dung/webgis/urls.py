from django.urls import path

from .api import views as api
from .views import khach, noi_bo

app_name = "webgis"
urlpatterns = [
    path("ban-do/", khach.ban_do, name="ban_do"),
    path("ban-do/api/tim-kiem/", api.tim_kiem, name="tim_kiem"),
    path("ban-do/api/chi-nhanh/", api.chi_nhanh_gan, name="chi_nhanh_gan"),
    path("ban-do/api/dat-giu/", api.tao_dat_giu, name="dat_giu"),
    path("ban-do/api/tim-dia-chi/", api.tim_dia_chi_api, name="tim_dia_chi"),
    path("ban-do/api/dia-chi-tu-toa-do/", api.dia_chi_tu_toa_do_api, name="dia_chi_tu_toa_do"),
    path("quan-ly/ban-do/ban-do-nhiet/", noi_bo.ban_do_nhiet, name="ban_do_nhiet"),
    path("quan-ly/ban-do/api/ban-do-nhiet/", api.ban_do_nhiet, name="du_lieu_nhiet"),
]
