from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Round
from django.urls import reverse
from django.utils import timezone

from ung_dung.chung.permissions import thay_toan_chuoi

from .models import (
    PHAN_TRAM_GIAM_TOI_DA,
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
    if not thay_toan_chuoi(nguoi):
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
    quan_tri = thay_toan_chuoi(nguoi)
    cac_chi_nhanh = ChiNhanh.objects.order_by("ma_chi_nhanh")
    if not quan_tri:
        cac_chi_nhanh = cac_chi_nhanh.filter(pk=nguoi.chi_nhanh_id)
    if not (ca_chi_nhanh_ngung and quan_tri):
        cac_chi_nhanh = cac_chi_nhanh.filter(dang_hoat_dong=True)
    return cac_chi_nhanh


def lay_chi_nhanh_cong_khai():
    """Chi nhánh đang hoạt động cho website khách: ảnh đại diện, danh sách ảnh (chỉ khóa, không tải
    bytea) và điểm trung bình của các đánh giá đang hiển thị."""
    anh_dau = AnhChiNhanh.objects.filter(chi_nhanh=OuterRef("pk")).order_by("thu_tu", "pk")
    dang_hien = Q(cac_danh_gia__dang_hien_thi=True)
    return (
        ChiNhanh.objects.filter(dang_hoat_dong=True)
        .annotate(
            id_anh_dai_dien=Subquery(anh_dau.values("pk")[:1]),
            diem_sao=Avg("cac_danh_gia__so_sao", filter=dang_hien),
            so_danh_gia=Count("cac_danh_gia", filter=dang_hien),
        )
        .prefetch_related(
            Prefetch("cac_anh", queryset=AnhChiNhanh.objects.only("pk", "chi_nhanh", "thu_tu"))
        )
        .order_by("ma_chi_nhanh")
    )


def du_lieu_ban_do_chi_nhanh(cn, quang_duong=None):
    """Một chi nhánh lấy từ lay_chi_nhanh_cong_khai() thành dữ liệu cho ghim và popup bản đồ.

    Dùng chung cho trang tìm nhà thuốc và bản đồ trang đặt hàng. `khoang_cach` có khi truy vấn đã
    chú thích ST_Distance tới vị trí của khách; `quang_duong` là quãng đường đi thực tế từ
    webgis.services.duong_di.quang_duong_tu_vi_tri (mét, phút xe máy, có phải ước tính không).
    """
    cac_anh = [reverse("danh_muc:anh_chi_nhanh", args=[anh.pk]) for anh in cn.cac_anh.all()]
    khoang_cach = getattr(cn, "khoang_cach", None)
    return {
        "id_chi_nhanh": cn.pk,
        "ma_chi_nhanh": cn.ma_chi_nhanh,
        "ten_chi_nhanh": cn.ten_chi_nhanh,
        "dia_chi": cn.dia_chi,
        "so_dien_thoai": cn.so_dien_thoai,
        "gio_mo_cua": cn.gio_mo_cua.strftime("%H:%M"),
        "gio_dong_cua": cn.gio_dong_cua.strftime("%H:%M"),
        "dang_mo_cua": cn.dang_mo_cua(),
        "vi_do": cn.vi_tri.y,
        "kinh_do": cn.vi_tri.x,
        "khoang_cach_met": round(khoang_cach.m, 1) if khoang_cach is not None else None,
        "quang_duong_met": quang_duong["quang_duong_met"] if quang_duong else None,
        "phut_xe_may": quang_duong["phut_xe_may"] if quang_duong else None,
        "quang_duong_uoc_tinh": quang_duong["uoc_tinh"] if quang_duong else False,
        "diem_sao": round(cn.diem_sao, 1) if cn.diem_sao else None,
        "so_danh_gia": cn.so_danh_gia,
        "anh": cac_anh[0] if cac_anh else "",
        "cac_anh": cac_anh,
        "duong_dan": reverse("danh_muc:khach_chi_nhanh_chi_tiet", args=[cn.ma_chi_nhanh]),
    }


def khuyen_mai_dang_ap_dung(ngay=None):
    ngay = ngay or timezone.localdate()
    return KhuyenMai.objects.filter(
        dang_hoat_dong=True,
        ngay_bat_dau__lte=ngay,
        ngay_ket_thuc__gte=ngay,
        phan_tram_giam__lte=PHAN_TRAM_GIAM_TOI_DA,
    )


def them_gia_va_anh(cac_thuoc, ngay=None):
    """Gắn phần trăm giảm đang áp dụng, đơn giá sau giảm và id ảnh đại diện.

    Đơn giá tính trong SQL bằng cùng quy tắc làm tròn của gia.tinh_don_gia để sắp
    xếp theo giá đúng với giá khách thấy.
    """
    # Thuốc kê đơn không được khuyến mại (Nghị định 81/2018/NĐ-CP Điều 5, sửa đổi bởi
    # Nghị định 239/2026/NĐ-CP; chỉ trừ khuyến mại cho thương nhân kinh doanh thuốc), nên
    # không áp giảm giá cho thuốc kê đơn.
    khuyen_mai = (
        khuyen_mai_dang_ap_dung(ngay)
        .filter(thuoc=OuterRef("pk"), thuoc__la_thuoc_ke_don=False)
        .order_by("-phan_tram_giam")
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


def lay_danh_gia(nguoi, loai):
    """Đánh giá thuốc dùng chung toàn chuỗi; đánh giá chi nhánh theo phạm vi chi nhánh của người xem."""
    from .models import DanhGiaChiNhanh, DanhGiaThuoc

    if loai == "chi_nhanh":
        tap_hop = DanhGiaChiNhanh.objects.select_related("chi_nhanh", "khach_hang")
        if not thay_toan_chuoi(nguoi):
            tap_hop = tap_hop.filter(chi_nhanh_id=nguoi.chi_nhanh_id)
        return tap_hop
    return DanhGiaThuoc.objects.select_related("thuoc", "khach_hang")
