from django.urls import path

from .views import chi_nhanh, don_vi_tinh, nha_cung_cap, nhan_vien, nhom_atc, quy_doi_bao_goi, thuoc

app_name = "danh_muc"
urlpatterns = [
    path("chi-nhanh/", chi_nhanh.danh_sach, name="chi_nhanh_danh_sach"),
    path("chi-nhanh/tao/", chi_nhanh.tao, name="chi_nhanh_tao"),
    path("chi-nhanh/<int:ma>/sua/", chi_nhanh.sua, name="chi_nhanh_sua"),
    path("don-vi-tinh/", don_vi_tinh.danh_sach, name="don_vi_tinh_danh_sach"),
    path("don-vi-tinh/tao/", don_vi_tinh.tao, name="don_vi_tinh_tao"),
    path("don-vi-tinh/<int:ma>/sua/", don_vi_tinh.sua, name="don_vi_tinh_sua"),
    path("nhom-atc/", nhom_atc.danh_sach, name="nhom_atc_danh_sach"),
    path("nhom-atc/tao/", nhom_atc.tao, name="nhom_atc_tao"),
    path("nhom-atc/<int:ma>/sua/", nhom_atc.sua, name="nhom_atc_sua"),
    path("nha-cung-cap/", nha_cung_cap.danh_sach, name="nha_cung_cap_danh_sach"),
    path("nha-cung-cap/tao/", nha_cung_cap.tao, name="nha_cung_cap_tao"),
    path("nha-cung-cap/<int:ma>/sua/", nha_cung_cap.sua, name="nha_cung_cap_sua"),
    path("thuoc/", thuoc.danh_sach, name="thuoc_danh_sach"),
    path("thuoc/tao/", thuoc.tao, name="thuoc_tao"),
    path("thuoc/<int:ma>/sua/", thuoc.sua, name="thuoc_sua"),
    path("quy-doi-bao-goi/", quy_doi_bao_goi.danh_sach, name="quy_doi_bao_goi_danh_sach"),
    path("quy-doi-bao-goi/tao/", quy_doi_bao_goi.tao, name="quy_doi_bao_goi_tao"),
    path("quy-doi-bao-goi/<int:ma>/sua/", quy_doi_bao_goi.sua, name="quy_doi_bao_goi_sua"),
    path("nhan-vien/", nhan_vien.danh_sach, name="nhan_vien_danh_sach"),
    path("nhan-vien/tao/", nhan_vien.tao, name="nhan_vien_tao"),
    path("nhan-vien/<int:ma>/sua/", nhan_vien.sua, name="nhan_vien_sua"),
]
