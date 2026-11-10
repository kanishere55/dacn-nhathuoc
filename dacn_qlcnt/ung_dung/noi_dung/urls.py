from django.urls import include, path

from .views import khach, quan_ly

app_name = "noi_dung"
quan_tri = [
    path("banner/", quan_ly.banner_danh_sach, name="banner_danh_sach"),
    path("banner/tao/", quan_ly.banner_sua, name="banner_tao"),
    path("banner/<int:ma>/sua/", quan_ly.banner_sua, name="banner_sua"),
    path("banner/<int:ma>/xoa/", quan_ly.banner_xoa, name="banner_xoa"),
    path("thong-tin/", quan_ly.thong_tin, name="thong_tin"),
    path("trang/", quan_ly.trang_danh_sach, name="trang_danh_sach"),
    path("trang/tao/", quan_ly.trang_sua, name="trang_tao"),
    path("trang/<int:ma>/sua/", quan_ly.trang_sua, name="trang_sua"),
    path("tin-tuc/", quan_ly.tin_tuc_danh_sach, name="tin_tuc_danh_sach"),
    path("tin-tuc/tao/", quan_ly.tin_tuc_sua, name="tin_tuc_tao"),
    path("tin-tuc/<int:ma>/sua/", quan_ly.tin_tuc_sua, name="tin_tuc_sua"),
]
urlpatterns = [
    path("trang/<slug:duong_dan>/", khach.trang, name="trang"),
    path("tin-tuc/", khach.tin_tuc_danh_sach, name="khach_tin_tuc_danh_sach"),
    path("tin-tuc/<slug:duong_dan>/", khach.tin_tuc_chi_tiet, name="khach_tin_tuc_chi_tiet"),
    path("anh/banner/<int:ma>/", khach.anh_banner, name="anh_banner"),
    path("nguon-hinh-anh/", khach.nguon_hinh_anh, name="nguon_hinh_anh"),
    path("quan-ly/noi-dung/", include(quan_tri)),
]
