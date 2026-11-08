from django.db.models import Q

from ung_dung.chung.permissions import la_quan_tri

from .models import ChiNhanh, DonViTinh, NhaCungCap, NhanVien, NhomATC, QuyDoiBaoGoi, Thuoc

DANH_MUC = {
    "chi_nhanh": (
        ChiNhanh,
        "Chi nhánh",
        ["ma_chi_nhanh", "ten_chi_nhanh", "dia_chi", "dang_hoat_dong"],
    ),
    "don_vi_tinh": (DonViTinh, "Đơn vị tính", ["ma_don_vi_tinh", "ten_don_vi_tinh"]),
    "nhom_atc": (NhomATC, "Nhóm ATC", ["ma_nhom_atc", "ten_nhom_atc"]),
    "nha_cung_cap": (
        NhaCungCap,
        "Nhà cung cấp",
        ["ma_nha_cung_cap", "ten_nha_cung_cap", "so_dien_thoai", "dang_hoat_dong"],
    ),
    "thuoc": (
        Thuoc,
        "Thuốc",
        ["ma_thuoc", "ten_thuoc", "don_vi_tinh", "gia_ban", "dang_hoat_dong"],
    ),
    "quy_doi_bao_goi": (QuyDoiBaoGoi, "Quy đổi bao gói", ["thuoc", "ten_quy_doi_bao_goi", "he_so"]),
    "nhan_vien": (
        NhanVien,
        "Nhân viên",
        ["ma_nhan_vien", "ten_nhan_vien", "tai_khoan", "so_dien_thoai"],
    ),
}


def lay_danh_muc(nguoi, loai, tu_khoa=""):
    model = DANH_MUC[loai][0]
    tap_hop = model.objects.all().order_by(model._meta.pk.name)
    if not la_quan_tri(nguoi):
        if loai == "chi_nhanh":
            tap_hop = tap_hop.filter(pk=nguoi.chi_nhanh_id)
        elif loai == "nhan_vien":
            tap_hop = tap_hop.filter(tai_khoan__chi_nhanh_id=nguoi.chi_nhanh_id)
    cac_cot_tim = [cot.name for cot in model._meta.fields if cot.name.startswith(("ma_", "ten_"))]
    if tu_khoa and cac_cot_tim:
        dieu_kien = Q()
        for cot in cac_cot_tim:
            dieu_kien |= Q(**{f"{cot}__icontains": tu_khoa})
        tap_hop = tap_hop.filter(dieu_kien)
    return tap_hop


def lay_chi_nhanh(nguoi, *, ca_chi_nhanh_ngung=False):
    quan_tri = la_quan_tri(nguoi)
    cac_chi_nhanh = ChiNhanh.objects.order_by("ma_chi_nhanh")
    if not quan_tri:
        cac_chi_nhanh = cac_chi_nhanh.filter(pk=nguoi.chi_nhanh_id)
    if not (ca_chi_nhanh_ngung and quan_tri):
        cac_chi_nhanh = cac_chi_nhanh.filter(dang_hoat_dong=True)
    return cac_chi_nhanh
