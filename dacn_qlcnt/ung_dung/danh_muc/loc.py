"""Cấu hình bộ lọc (ô tìm kiếm và danh mục thả xuống) cho từng danh sách trong khu quản lý."""

from django.utils import timezone

from ung_dung.chung.loc_danh_sach import BoLoc, OChon

from .models import ChiNhanh, DanhMucSanPham, DonViTinh, NhomATC, Thuoc

HOAT_DONG = [("co", "Đang hoạt động"), ("khong", "Đã ngừng")]
CO_KHONG = [("co", "Có"), ("khong", "Không")]


def _loc_co_khong(cot):
    return lambda tap_hop, gia_tri: tap_hop.filter(**{cot: gia_tri == "co"})


def _o_hoat_dong(cot="dang_hoat_dong", nhan="Trạng thái", lua_chon=None):
    return OChon("trang_thai", nhan, lua_chon or HOAT_DONG, ham_loc=_loc_co_khong(cot))


def _lua_chon(model, nhan_cot, *, loc=None):
    cac_doi_tuong = model.objects.all() if loc is None else model.objects.filter(**loc)
    return [(doi_tuong.pk, getattr(doi_tuong, nhan_cot)) for doi_tuong in cac_doi_tuong]


def _loc_khuyen_mai(tap_hop, gia_tri):
    hom_nay = timezone.localdate()
    if gia_tri == "dang_ap_dung":
        return tap_hop.filter(
            dang_hoat_dong=True, ngay_bat_dau__lte=hom_nay, ngay_ket_thuc__gte=hom_nay
        )
    if gia_tri == "sap_dien_ra":
        return tap_hop.filter(dang_hoat_dong=True, ngay_bat_dau__gt=hom_nay)
    if gia_tri == "het_han":
        return tap_hop.filter(ngay_ket_thuc__lt=hom_nay)
    return tap_hop.filter(dang_hoat_dong=False)


def tao_bo_loc(request, loai):
    """Bộ lọc của danh sách `loai`; ô chọn lấy lựa chọn từ CSDL tại thời điểm vẽ trang."""
    if loai == "thuoc":
        return BoLoc(
            request,
            cac_cot_tim=("ma_thuoc", "ten_thuoc", "hoat_chat", "nha_san_xuat"),
            nhan_tim="Mã, tên thuốc, hoạt chất, nhà sản xuất",
            cac_o_chon=[
                OChon(
                    "danh_muc",
                    "Danh mục",
                    _lua_chon(DanhMucSanPham, "ten_danh_muc_san_pham"),
                    "danh_muc_san_pham_id",
                ),
                OChon("nhom_atc", "Nhóm ATC", _lua_chon(NhomATC, "ma_nhom_atc"), "nhom_atc_id"),
                OChon(
                    "don_vi",
                    "Đơn vị cơ sở",
                    _lua_chon(DonViTinh, "ten_don_vi_tinh"),
                    "don_vi_tinh_id",
                ),
                OChon(
                    "ke_don",
                    "Kê đơn",
                    [("co", "Thuốc kê đơn"), ("khong", "Không kê đơn")],
                    ham_loc=_loc_co_khong("la_thuoc_ke_don"),
                ),
                _o_hoat_dong(),
                OChon(
                    "co_anh",
                    "Ảnh",
                    [("co", "Đã có ảnh"), ("khong", "Chưa có ảnh")],
                    ham_loc=lambda tap_hop, gia_tri: tap_hop.filter(
                        cac_anh__isnull=gia_tri == "khong"
                    ).distinct(),
                ),
            ],
        )
    if loai == "chi_nhanh":
        return BoLoc(
            request,
            cac_cot_tim=("ma_chi_nhanh", "ten_chi_nhanh", "dia_chi", "so_dien_thoai"),
            nhan_tim="Mã, tên, địa chỉ, số điện thoại",
            cac_o_chon=[
                _o_hoat_dong(),
                OChon(
                    "co_anh",
                    "Ảnh",
                    [("co", "Đã có ảnh"), ("khong", "Chưa có ảnh")],
                    ham_loc=lambda tap_hop, gia_tri: tap_hop.filter(
                        cac_anh__isnull=gia_tri == "khong"
                    ).distinct(),
                ),
            ],
        )
    if loai == "nha_cung_cap":
        return BoLoc(
            request,
            cac_cot_tim=("ma_nha_cung_cap", "ten_nha_cung_cap", "dia_chi", "so_dien_thoai"),
            nhan_tim="Mã, tên, địa chỉ, số điện thoại",
            cac_o_chon=[_o_hoat_dong()],
        )
    if loai == "nhan_vien":
        return BoLoc(
            request,
            cac_cot_tim=(
                "ma_nhan_vien",
                "ten_nhan_vien",
                "so_dien_thoai",
                "tai_khoan__ten_dang_nhap",
            ),
            nhan_tim="Mã, họ tên, số điện thoại, tên đăng nhập",
            cac_o_chon=[
                OChon(
                    "chi_nhanh",
                    "Chi nhánh",
                    _lua_chon(ChiNhanh, "ten_chi_nhanh"),
                    "tai_khoan__chi_nhanh_id",
                )
            ],
        )
    if loai == "quy_doi_bao_goi":
        return BoLoc(
            request,
            cac_cot_tim=("ten_quy_doi_bao_goi", "thuoc__ten_thuoc", "thuoc__ma_thuoc"),
            nhan_tim="Tên bao gói, tên hoặc mã thuốc",
            cac_o_chon=[
                OChon("thuoc", "Thuốc", _lua_chon(Thuoc, "ten_thuoc"), "thuoc_id"),
            ],
        )
    if loai == "khuyen_mai":
        return BoLoc(
            request,
            cac_cot_tim=("ma_khuyen_mai", "ten_khuyen_mai", "thuoc__ten_thuoc", "thuoc__ma_thuoc"),
            nhan_tim="Mã, tên chương trình, thuốc",
            cac_o_chon=[
                OChon(
                    "trang_thai",
                    "Trạng thái",
                    [
                        ("dang_ap_dung", "Đang áp dụng"),
                        ("sap_dien_ra", "Sắp diễn ra"),
                        ("het_han", "Đã hết hạn"),
                        ("da_dung", "Đã dừng"),
                    ],
                    ham_loc=_loc_khuyen_mai,
                ),
                OChon("thuoc", "Thuốc", _lua_chon(Thuoc, "ten_thuoc"), "thuoc_id"),
            ],
        )
    if loai == "danh_muc_san_pham":
        return BoLoc(
            request,
            cac_cot_tim=("ma_danh_muc_san_pham", "ten_danh_muc_san_pham", "mo_ta"),
            nhan_tim="Mã, tên, mô tả danh mục",
            cac_o_chon=[_o_hoat_dong("dang_hien_thi", "Hiển thị", CO_KHONG)],
        )
    if loai == "nhom_atc":
        return BoLoc(
            request,
            cac_cot_tim=("ma_nhom_atc", "ten_nhom_atc"),
            nhan_tim="Mã ATC hoặc diễn giải",
        )
    return BoLoc(request, cac_cot_tim=("ma_don_vi_tinh", "ten_don_vi_tinh"), nhan_tim="Mã hoặc tên")
