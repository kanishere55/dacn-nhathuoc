from django.urls import path

from .views import don_dat_giu, phieu_ban

app_name = "ban_hang"
urlpatterns = [
    path("phieu-ban/", phieu_ban.danh_sach, name="phieu_ban_danh_sach"),
    path("phieu-ban/tao/", phieu_ban.tao, name="phieu_ban_tao"),
    path("phieu-ban/<int:ma>/", phieu_ban.chi_tiet, name="phieu_ban_chi_tiet"),
    path("don-dat-giu/", don_dat_giu.danh_sach, name="don_dat_giu_danh_sach"),
    path("don-dat-giu/<int:ma>/", don_dat_giu.chi_tiet, name="don_dat_giu_chi_tiet"),
    path("don-dat-giu/<int:ma>/huy/", don_dat_giu.huy, name="don_dat_giu_huy"),
    path("don-dat-giu/<int:ma>/nhan/", don_dat_giu.nhan, name="don_dat_giu_nhan"),
]
