from django.urls import path

from .views import noi_bo

app_name = "thong_bao"
urlpatterns = [
    path("quan-ly/email/", noi_bo.nhat_ky_email, name="nhat_ky_email"),
]
