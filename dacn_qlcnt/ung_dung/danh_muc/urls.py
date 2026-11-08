from django.urls import include, path, register_converter

from .views import (
    anh,
    chi_nhanh,
    danh_muc_san_pham,
    don_vi_tinh,
    khach,
    khuyen_mai,
    nha_cung_cap,
    nhan_vien,
    nhom_atc,
    quy_doi_bao_goi,
    thuoc,
)


class LoaiAnh:
    """Đường dẫn quản lý ảnh dùng tên bảng sở hữu: thuoc hoặc chi_nhanh."""

    regex = "thuoc|chi_nhanh"

    def to_python(self, gia_tri):
        return gia_tri

    def to_url(self, gia_tri):
        return gia_tri


register_converter(LoaiAnh, "loai_anh")

app_name = "danh_muc"
quan_ly = [
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
    path("danh-muc-san-pham/", danh_muc_san_pham.danh_sach, name="danh_muc_san_pham_danh_sach"),
    path("danh-muc-san-pham/tao/", danh_muc_san_pham.tao, name="danh_muc_san_pham_tao"),
    path("danh-muc-san-pham/<int:ma>/sua/", danh_muc_san_pham.sua, name="danh_muc_san_pham_sua"),
    path("khuyen-mai/", khuyen_mai.danh_sach, name="khuyen_mai_danh_sach"),
    path("khuyen-mai/tao/", khuyen_mai.tao, name="khuyen_mai_tao"),
    path("khuyen-mai/<int:ma>/sua/", khuyen_mai.sua, name="khuyen_mai_sua"),
    path("<loai_anh:loai>/<int:ma>/anh/", anh.tai_len, name="anh_tai_len"),
    path("<loai_anh:loai>/<int:ma>/anh/<int:id_anh>/xoa/", anh.xoa, name="anh_xoa"),
    path(
        "<loai_anh:loai>/<int:ma>/anh/<int:id_anh>/dai-dien/",
        anh.dat_dai_dien,
        name="anh_dai_dien",
    ),
]
urlpatterns = [
    path("anh/thuoc/<int:ma>/", anh.anh_thuoc, name="anh_thuoc"),
    path("anh/chi-nhanh/<int:ma>/", anh.anh_chi_nhanh, name="anh_chi_nhanh"),
    path("thuoc/", khach.danh_sach_thuoc, name="khach_thuoc_danh_sach"),
    path("thuoc/<str:ma>/", khach.chi_tiet_thuoc, name="khach_thuoc_chi_tiet"),
    path("chi-nhanh/<str:ma>/", khach.chi_tiet_chi_nhanh, name="khach_chi_nhanh_chi_tiet"),
    path("quan-ly/danh-muc/", include(quan_ly)),
]
