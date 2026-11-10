from django.urls import path

from .views import khach, noi_bo

app_name = "tro_chuyen"
urlpatterns = [
    path("tro-chuyen/", khach.danh_sach, name="khach_danh_sach"),
    path("tro-chuyen/<int:ma>/", khach.chi_tiet, name="khach_chi_tiet"),
    path("tro-chuyen/<int:ma>/tin-cu/", khach.tin_cu, name="khach_tin_cu"),
    path("tro-chuyen/<int:ma>/gui-tin/", khach.gui_tin, name="khach_gui_tin"),
    path("tro-chuyen/anh/<int:ma>/", khach.anh, name="khach_anh"),
    path("tro-chuyen/don-hang/<int:ma>/", khach.tu_don_hang, name="khach_tu_don_hang"),
    path("tro-chuyen/chua-doc/", khach.so_chua_doc, name="so_chua_doc"),
    path("tro-chuyen/luu-y/", khach.luu_y, name="khach_luu_y"),
    path("quan-ly/tro-chuyen/", noi_bo.danh_sach, name="danh_sach"),
    path("quan-ly/tro-chuyen/<int:ma>/", noi_bo.chi_tiet, name="chi_tiet"),
    path("quan-ly/tro-chuyen/<int:ma>/tin-cu/", noi_bo.tin_cu, name="tin_cu"),
    path("quan-ly/tro-chuyen/<int:ma>/gui-tin/", noi_bo.gui_tin, name="gui_tin"),
    path("quan-ly/tro-chuyen/anh/<int:ma>/", noi_bo.anh, name="anh"),
    path("quan-ly/tro-chuyen/<int:ma>/xong/", noi_bo.xong, name="xong"),
    path("quan-ly/tro-chuyen/<int:ma>/mo-lai/", noi_bo.mo_lai_phong, name="mo_lai"),
    path("quan-ly/tro-chuyen/don-hang/<int:ma>/", noi_bo.tu_don_hang, name="tu_don_hang"),
]
