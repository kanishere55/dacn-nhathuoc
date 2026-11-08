from django.db.models import (
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Round
from django.utils import timezone

from ung_dung.chung.permissions import la_quan_tri

from .models import (
    AnhChiNhanh,
    AnhThuoc,
    ChiNhanh,
    DanhMucSanPham,
    DonViTinh,
    KhuyenMai,
    NhaCungCap,
    NhanVien,
    NhomATC,
    QuyDoiBaoGoi,
    Thuoc,
)

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
    "danh_muc_san_pham": (
        DanhMucSanPham,
        "Danh mục sản phẩm",
        ["ma_danh_muc_san_pham", "ten_danh_muc_san_pham", "thu_tu", "dang_hien_thi"],
    ),
    "khuyen_mai": (
        KhuyenMai,
        "Khuyến mãi",
        [
            "ma_khuyen_mai",
            "ten_khuyen_mai",
            "thuoc",
            "phan_tram_giam",
            "ngay_bat_dau",
            "ngay_ket_thuc",
            "dang_hoat_dong",
        ],
    ),
}
# Bảng có ảnh quản lý ngay trên trang sửa.
CO_ANH = {"thuoc": (Thuoc, AnhThuoc, "thuoc"), "chi_nhanh": (ChiNhanh, AnhChiNhanh, "chi_nhanh")}
SAP_XEP_THUOC = {
    "ten": ("ten_thuoc", "ma_thuoc"),
    "gia_tang": ("don_gia", "ten_thuoc"),
    "gia_giam": ("-don_gia", "ten_thuoc"),
    "giam_nhieu": ("-phan_tram_giam", "ten_thuoc"),
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


def lay_chi_nhanh_cong_khai():
    anh_dau = AnhChiNhanh.objects.filter(chi_nhanh=OuterRef("pk")).order_by("thu_tu", "pk")
    return (
        ChiNhanh.objects.filter(dang_hoat_dong=True)
        .annotate(id_anh_dai_dien=Subquery(anh_dau.values("pk")[:1]))
        .order_by("ma_chi_nhanh")
    )


def khuyen_mai_dang_ap_dung(ngay=None):
    ngay = ngay or timezone.localdate()
    return KhuyenMai.objects.filter(
        dang_hoat_dong=True, ngay_bat_dau__lte=ngay, ngay_ket_thuc__gte=ngay
    )


def them_gia_va_anh(cac_thuoc, ngay=None):
    """Gắn phần trăm giảm đang áp dụng, đơn giá sau giảm và id ảnh đại diện.

    Đơn giá tính trong SQL bằng cùng quy tắc làm tròn của gia.tinh_don_gia để sắp
    xếp theo giá đúng với giá khách thấy.
    """
    khuyen_mai = (
        khuyen_mai_dang_ap_dung(ngay).filter(thuoc=OuterRef("pk")).order_by("-phan_tram_giam")
    )
    anh_dau = AnhThuoc.objects.filter(thuoc=OuterRef("pk")).order_by("thu_tu", "pk")
    return cac_thuoc.annotate(
        phan_tram_giam=Coalesce(Subquery(khuyen_mai.values("phan_tram_giam")[:1]), Value(0)),
        ten_khuyen_mai=Subquery(khuyen_mai.values("ten_khuyen_mai")[:1]),
        ngay_het_khuyen_mai=Subquery(khuyen_mai.values("ngay_ket_thuc")[:1]),
        id_anh_dai_dien=Subquery(anh_dau.values("pk")[:1]),
    ).annotate(
        don_gia=Case(
            When(phan_tram_giam=0, then=F("gia_ban")),
            default=ExpressionWrapper(
                Round(F("gia_ban") - F("gia_ban") * F("phan_tram_giam") / Value(100)),
                output_field=DecimalField(max_digits=14, decimal_places=0),
            ),
            output_field=DecimalField(max_digits=14, decimal_places=0),
        )
    )


def lay_thuoc_cong_khai(
    tu_khoa="", ma_nhom="", *, ma_danh_muc="", khong_ke_don=False, dang_giam=False, sap_xep="ten"
):
    cac_thuoc = them_gia_va_anh(
        Thuoc.objects.filter(dang_hoat_dong=True).select_related(
            "don_vi_tinh", "nhom_atc", "danh_muc_san_pham"
        )
    )
    if tu_khoa:
        cac_thuoc = cac_thuoc.filter(
            Q(ten_thuoc__icontains=tu_khoa)
            | Q(ma_thuoc__icontains=tu_khoa)
            | Q(hoat_chat__icontains=tu_khoa)
        )
    if ma_nhom:
        cac_thuoc = cac_thuoc.filter(nhom_atc__ma_nhom_atc=ma_nhom)
    if ma_danh_muc:
        cac_thuoc = cac_thuoc.filter(danh_muc_san_pham__ma_danh_muc_san_pham=ma_danh_muc)
    if khong_ke_don:
        cac_thuoc = cac_thuoc.filter(la_thuoc_ke_don=False)
    if dang_giam:
        cac_thuoc = cac_thuoc.filter(phan_tram_giam__gt=0)
    return cac_thuoc.order_by(*SAP_XEP_THUOC.get(sap_xep, SAP_XEP_THUOC["ten"]))


def lay_nhom_thuoc_cong_khai():
    return NhomATC.objects.filter(thuoc__dang_hoat_dong=True).distinct().order_by("ma_nhom_atc")


def lay_danh_muc_san_pham_cong_khai():
    from django.db.models import Count

    return DanhMucSanPham.objects.filter(dang_hien_thi=True).annotate(
        so_thuoc=Count("thuoc", filter=Q(thuoc__dang_hoat_dong=True))
    )


def lay_anh(loai):
    return CO_ANH[loai][1].objects.all()
