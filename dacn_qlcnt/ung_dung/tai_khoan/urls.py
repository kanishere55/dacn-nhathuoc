from django.urls import path

from .views import ho_so, khach, nhom_quyen, noi_bo

app_name = "tai_khoan"
urlpatterns = [
    path("tai-khoan/dang-nhap/", khach.dang_nhap, name="dang_nhap"),
    path("tai-khoan/dang-xuat/", khach.dang_xuat, name="dang_xuat"),
    path("tai-khoan/dang-ky/", khach.dang_ky, name="dang_ky"),
    path("tai-khoan/dang-ky/<uuid:ma>/", khach.xac_thuc_dang_ky, name="xac_thuc_dang_ky"),
    path("tai-khoan/xac-thuc/<uuid:ma>/gui-lai/", khach.gui_lai_ma, name="gui_lai_ma"),
    path("tai-khoan/quen-mat-khau/", khach.quen_mat_khau, name="quen_mat_khau"),
    path("tai-khoan/quen-mat-khau/<uuid:ma>/", khach.dat_lai_mat_khau, name="dat_lai_mat_khau"),
    path("tai-khoan/quen-ten-dang-nhap/", khach.quen_ten_dang_nhap, name="quen_ten_dang_nhap"),
    path(
        "tai-khoan/khoi-phuc-email/<uuid:ma>/<str:khoa>/",
        khach.hoan_tac_doi_email,
        name="hoan_tac_doi_email",
    ),
    path("tai-khoan-cua-toi/", ho_so.cua_toi, name="cua_toi"),
    path("tai-khoan-cua-toi/thong-tin/", ho_so.thong_tin, name="thong_tin"),
    path("tai-khoan-cua-toi/mat-khau/", ho_so.doi_mat_khau, name="doi_mat_khau"),
    path("tai-khoan-cua-toi/email/", ho_so.doi_email, name="doi_email"),
    path("tai-khoan-cua-toi/email/<uuid:ma>/", ho_so.xac_thuc_doi_email, name="xac_thuc_doi_email"),
    path("tai-khoan-cua-toi/dia-chi/", ho_so.so_dia_chi, name="so_dia_chi"),
    path("tai-khoan-cua-toi/dia-chi/them/", ho_so.luu_dia_chi, name="them_dia_chi"),
    path("tai-khoan-cua-toi/dia-chi/<int:ma>/sua/", ho_so.luu_dia_chi, name="sua_dia_chi"),
    path("tai-khoan-cua-toi/dia-chi/<int:ma>/xoa/", ho_so.xoa_dia_chi, name="xoa_dia_chi"),
    path(
        "tai-khoan-cua-toi/dia-chi/<int:ma>/mac-dinh/",
        ho_so.dat_dia_chi_mac_dinh,
        name="dat_dia_chi_mac_dinh",
    ),
    path("quan-ly/tai-khoan/", noi_bo.danh_sach, name="danh_sach"),
    path("quan-ly/tai-khoan/tao/", noi_bo.chinh_sua, name="tao"),
    path("quan-ly/tai-khoan/<int:ma>/sua/", noi_bo.chinh_sua, name="sua"),
    path("quan-ly/nhom-quyen/", nhom_quyen.danh_sach, name="nhom_quyen_danh_sach"),
    path("quan-ly/nhom-quyen/tao/", nhom_quyen.chinh_sua, name="nhom_quyen_tao"),
    path("quan-ly/nhom-quyen/<int:ma>/sua/", nhom_quyen.chinh_sua, name="nhom_quyen_sua"),
    path("quan-ly/nhom-quyen/<int:ma>/xoa/", nhom_quyen.xoa, name="nhom_quyen_xoa"),
]
