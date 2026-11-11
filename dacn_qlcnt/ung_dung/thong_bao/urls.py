from django.urls import path

from .views import noi_bo

app_name = "thong_bao"
urlpatterns = [
    path("quan-ly/email/", noi_bo.nhat_ky_email, name="nhat_ky_email"),
    path("quan-ly/email/<int:ma>/", noi_bo.chi_tiet, name="nhat_ky_email_chi_tiet"),
    path("quan-ly/email/<int:ma>/gui-lai/", noi_bo.gui_lai_thu, name="nhat_ky_email_gui_lai"),
]
