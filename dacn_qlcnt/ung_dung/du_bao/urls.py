from django.urls import path

from . import views

app_name = "du_bao"
urlpatterns = [path("", views.ket_qua, name="ket_qua")]
