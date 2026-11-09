from django.urls import path

from .views import (
    lo_thuoc,
    phieu_dieu_chuyen,
    phieu_kiem_ke,
    phieu_nhap,
    phieu_tra_nha_cung_cap,
    phieu_xuat_huy,
    ton_kho,
)

app_name = "kho"
urlpatterns = [
    path("lo-thuoc/", lo_thuoc.danh_sach, name="lo_thuoc_danh_sach"),
    path(
        "lo-thuoc/<int:ma>/doi-trang-thai/", lo_thuoc.doi_trang_thai, name="lo_thuoc_doi_trang_thai"
    ),
    path("ton-kho/", ton_kho.danh_sach, name="ton_kho_danh_sach"),
    path("canh-bao/", ton_kho.canh_bao, name="canh_bao"),
]
for ten, duong_dan, module in [
    ("phieu_nhap", "phieu-nhap", phieu_nhap),
    ("phieu_tra", "phieu-tra-nha-cung-cap", phieu_tra_nha_cung_cap),
    ("phieu_dieu_chuyen", "phieu-dieu-chuyen", phieu_dieu_chuyen),
    ("phieu_kiem_ke", "phieu-kiem-ke", phieu_kiem_ke),
    ("phieu_xuat_huy", "phieu-xuat-huy", phieu_xuat_huy),
]:
    urlpatterns += [
        path(f"{duong_dan}/", module.danh_sach, name=f"{ten}_danh_sach"),
        path(f"{duong_dan}/tao/", module.tao, name=f"{ten}_tao"),
        path(f"{duong_dan}/<int:ma>/", module.chi_tiet, name=f"{ten}_chi_tiet"),
        path(f"{duong_dan}/<int:ma>/pdf/", module.pdf, name=f"{ten}_pdf"),
    ]
