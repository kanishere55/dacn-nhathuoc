from django.urls import include, path

from .views import don_dat_giu, khach, phieu_ban

app_name = "ban_hang"
quan_ly = [
    path("phieu-ban/", phieu_ban.danh_sach, name="phieu_ban_danh_sach"),
    path("phieu-ban/tao/", phieu_ban.tao, name="phieu_ban_tao"),
    path("phieu-ban/<int:ma>/", phieu_ban.chi_tiet, name="phieu_ban_chi_tiet"),
    path("don-dat-giu/", don_dat_giu.danh_sach, name="don_dat_giu_danh_sach"),
    path("don-dat-giu/<int:ma>/", don_dat_giu.chi_tiet, name="don_dat_giu_chi_tiet"),
    path("don-dat-giu/<int:ma>/huy/", don_dat_giu.huy, name="don_dat_giu_huy"),
    path("don-dat-giu/<int:ma>/nhan/", don_dat_giu.nhan, name="don_dat_giu_nhan"),
]
urlpatterns = [
    path("gio-dat-giu/", khach.gio_dat_giu, name="gio_dat_giu"),
    path("gio-dat-giu/them/<str:ma>/", khach.them_vao_gio, name="gio_dat_giu_them"),
    path("gio-dat-giu/sua/<int:ma>/", khach.sua_gio, name="gio_dat_giu_sua"),
    path("gio-dat-giu/xac-nhan/", khach.xac_nhan_dat_giu, name="gio_dat_giu_xac_nhan"),
    path("don-dat-giu/", khach.danh_sach_don, name="khach_don_dat_giu_danh_sach"),
    path("don-dat-giu/<int:ma>/", khach.chi_tiet_don, name="khach_don_dat_giu_chi_tiet"),
    path("don-dat-giu/<int:ma>/huy/", khach.huy_don, name="khach_don_dat_giu_huy"),
    path("quan-ly/ban-hang/", include(quan_ly)),
]
