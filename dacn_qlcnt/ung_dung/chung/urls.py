from django.urls import path

from . import views

app_name = "chung"
urlpatterns = [path("", views.trang_chu, name="trang_chu")]
