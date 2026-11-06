from django.urls import path

from . import views
from .api import views as api

app_name = "webgis"
urlpatterns = [
    path("", views.ban_do, name="ban_do"),
    path("ban-do-nhiet/", views.ban_do_nhiet, name="ban_do_nhiet"),
    path("api/tim-kiem/", api.tim_kiem, name="tim_kiem"),
    path("api/dat-giu/", api.tao_dat_giu, name="dat_giu"),
    path("api/ban-do-nhiet/", api.ban_do_nhiet, name="du_lieu_nhiet"),
]
