from django.urls import path

from . import views

app_name = "bao_cao"
urlpatterns = [path("", views.tong_hop, name="tong_hop")]
