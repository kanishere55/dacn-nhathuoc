from django.urls import include, path

from .views import (
    don_hang,
    khach_dat_hang,
    khach_don_hang,
    khach_gio_hang,
    phieu_ban,
    tra_hang,
    xuat_hoa_don,
)

app_name = "ban_hang"
quan_ly = [
    path("phieu-ban/", phieu_ban.danh_sach, name="phieu_ban_danh_sach"),
    path("phieu-ban/tao/", phieu_ban.tao, name="phieu_ban_tao"),
    path("phieu-ban/<int:ma>/", phieu_ban.chi_tiet, name="phieu_ban_chi_tiet"),
    path("phieu-ban/<int:ma>/hoa-don/", phieu_ban.hoa_don_in, name="phieu_ban_in"),
    path("phieu-ban/<int:ma>/hoa-don.pdf", phieu_ban.hoa_don_pdf, name="phieu_ban_pdf"),
    path("don-hang/", don_hang.danh_sach, name="don_hang_danh_sach"),
    path("don-hang/<int:ma>/", don_hang.chi_tiet, name="don_hang_chi_tiet"),
    path("don-hang/<int:ma>/<slug:hanh_dong>/", don_hang.xu_ly, name="don_hang_xu_ly"),
    path("tra-hang/", tra_hang.danh_sach, name="tra_hang_danh_sach"),
    path("tra-hang/<int:ma>/", tra_hang.chi_tiet, name="tra_hang_chi_tiet"),
    path("tra-hang/<int:ma>/ghi-huy/", tra_hang.ghi_huy, name="tra_hang_huy"),
    path("tra-hang/<int:ma>/<slug:hanh_dong>/", tra_hang.xu_ly, name="tra_hang_xu_ly"),
    path("hoa-don-cong-ty/", xuat_hoa_don.danh_sach, name="xuat_hoa_don_danh_sach"),
    path("hoa-don-cong-ty/<int:ma>/xu-ly/", xuat_hoa_don.xu_ly, name="xuat_hoa_don_xu_ly"),
]
urlpatterns = [
    path("gio-hang/", khach_gio_hang.gio_hang, name="gio_hang"),
    path("gio-hang/them/<str:ma>/", khach_gio_hang.them_vao_gio, name="gio_hang_them"),
    path("gio-hang/sua/<int:ma>/", khach_gio_hang.sua_gio, name="gio_hang_sua"),
    path("dat-hang/", khach_dat_hang.dat_hang, name="dat_hang"),
    path("don-hang/", khach_don_hang.danh_sach, name="khach_don_hang_danh_sach"),
    path("don-hang/<int:ma>/", khach_don_hang.chi_tiet, name="khach_don_hang_chi_tiet"),
    path("don-hang/<int:ma>/huy/", khach_don_hang.huy, name="khach_don_hang_huy"),
    path(
        "don-hang/<int:ma>/da-nhan-hang/",
        khach_don_hang.da_nhan_hang,
        name="khach_don_hang_da_nhan",
    ),
    path("don-hang/<int:ma>/hoa-don/", khach_don_hang.hoa_don_in, name="khach_hoa_don_in"),
    path("don-hang/<int:ma>/tra-hang/", tra_hang.khach_tao, name="khach_tra_hang"),
    path(
        "don-hang/<int:ma>/hoa-don-cong-ty/",
        khach_don_hang.yeu_cau_hoa_don_cong_ty,
        name="khach_hoa_don_cong_ty",
    ),
    path("anh-tra-hang/<int:ma>/", tra_hang.anh, name="anh_tra_hang"),
    path("don-hang/<int:ma>/hoa-don.pdf", khach_don_hang.hoa_don_pdf, name="khach_hoa_don_pdf"),
    path("quan-ly/ban-hang/", include(quan_ly)),
]
