from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from ung_dung.ban_hang.forms import ThemThuocVaoGioForm
from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import AnhChiNhanh, AnhThuoc
from ..selectors import (
    SAP_XEP_THUOC,
    lay_chi_nhanh_cong_khai,
    lay_danh_muc_san_pham_cong_khai,
    lay_nhom_thuoc_cong_khai,
    lay_thuoc_cong_khai,
)

TEN_SAP_XEP = {
    "ten": "Tên A–Z",
    "gia_tang": "Giá thấp đến cao",
    "gia_giam": "Giá cao đến thấp",
    "giam_nhieu": "Giảm giá nhiều",
}


@require_GET
def danh_sach_thuoc(request):
    bo_loc = {
        "tu_khoa": cat_khoang_trang(request.GET.get("q", ""))[:150],
        "ma_nhom": request.GET.get("nhom", "")[:32],
        "ma_danh_muc": request.GET.get("danh_muc", "")[:32],
        "khong_ke_don": request.GET.get("khong_ke_don") == "1",
        "dang_giam": request.GET.get("dang_giam") == "1",
        "sap_xep": request.GET.get("sap_xep", "ten")
        if request.GET.get("sap_xep") in SAP_XEP_THUOC
        else "ten",
    }
    cac_thuoc = lay_thuoc_cong_khai(
        bo_loc["tu_khoa"],
        bo_loc["ma_nhom"],
        ma_danh_muc=bo_loc["ma_danh_muc"],
        khong_ke_don=bo_loc["khong_ke_don"],
        dang_giam=bo_loc["dang_giam"],
        sap_xep=bo_loc["sap_xep"],
    )
    cac_danh_muc = list(lay_danh_muc_san_pham_cong_khai())
    return render(
        request,
        "danh_muc/khach/danh_sach_thuoc.html",
        {
            "trang": Paginator(cac_thuoc, 12).get_page(request.GET.get("page")),
            "bo_loc": bo_loc,
            "cac_nhom": lay_nhom_thuoc_cong_khai(),
            "cac_danh_muc": cac_danh_muc,
            "danh_muc_chon": next(
                (dm for dm in cac_danh_muc if dm.ma_danh_muc_san_pham == bo_loc["ma_danh_muc"]),
                None,
            ),
            "ten_sap_xep": TEN_SAP_XEP,
        },
    )


@require_GET
def chi_tiet_thuoc(request, ma):
    thuoc = get_object_or_404(lay_thuoc_cong_khai(), ma_thuoc=ma)
    cac_anh = AnhThuoc.objects.filter(thuoc=thuoc).defer("noi_dung_anh")
    cung_danh_muc = (
        lay_thuoc_cong_khai(ma_danh_muc=thuoc.danh_muc_san_pham.ma_danh_muc_san_pham).exclude(
            pk=thuoc.pk
        )[:4]
        if thuoc.danh_muc_san_pham_id
        else []
    )
    cac_muc_noi_dung = [
        (tieu_de, noi_dung)
        for tieu_de, noi_dung in (
            ("Công dụng", thuoc.cong_dung),
            ("Liều dùng và cách dùng", thuoc.cach_dung),
            ("Chống chỉ định", thuoc.chong_chi_dinh),
            ("Tác dụng không mong muốn", thuoc.tac_dung_phu),
            ("Thận trọng, lưu ý", thuoc.luu_y),
            ("Bảo quản", thuoc.bao_quan),
        )
        if noi_dung
    ]
    return render(
        request,
        "danh_muc/khach/chi_tiet_thuoc.html",
        {
            "thuoc": thuoc,
            "cac_anh": cac_anh,
            "cac_muc_noi_dung": cac_muc_noi_dung,
            "cung_danh_muc": cung_danh_muc,
            "form_them": ThemThuocVaoGioForm(initial={"so_luong": 1}),
        },
    )


@require_GET
def chi_tiet_chi_nhanh(request, ma):
    chi_nhanh = get_object_or_404(lay_chi_nhanh_cong_khai(), ma_chi_nhanh=ma)
    bay_gio = timezone.localtime().time()
    return render(
        request,
        "danh_muc/khach/chi_tiet_chi_nhanh.html",
        {
            "chi_nhanh": chi_nhanh,
            "cac_anh": AnhChiNhanh.objects.filter(chi_nhanh=chi_nhanh).defer("noi_dung_anh"),
            "dang_mo_cua": chi_nhanh.gio_mo_cua <= bay_gio < chi_nhanh.gio_dong_cua,
        },
    )
