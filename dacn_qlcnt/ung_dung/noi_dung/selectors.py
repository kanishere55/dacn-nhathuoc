from types import SimpleNamespace

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import BannerTrangChu, ThongTinCuaHang, TinTuc, TrangNoiDung


def thong_tin_cua_hang():
    """Hàng cấu hình duy nhất; chưa nhập thì dùng giá trị mặc định từ settings."""
    thong_tin = ThongTinCuaHang.objects.filter(pk=1).first()
    if thong_tin:
        return thong_tin
    return SimpleNamespace(
        ten_thuong_hieu=settings.TEN_THUONG_HIEU,
        khau_hieu="",
        hotline="",
        email_lien_he="",
        dia_chi_tru_so="",
        gio_lam_viec="",
        giay_phep_kinh_doanh="",
    )


def banner_dang_hien(ngay=None):
    ngay = ngay or timezone.localdate()
    return (
        BannerTrangChu.objects.filter(dang_hien_thi=True)
        .filter(Q(ngay_bat_dau__isnull=True) | Q(ngay_bat_dau__lte=ngay))
        .filter(Q(ngay_ket_thuc__isnull=True) | Q(ngay_ket_thuc__gte=ngay))
        .defer("noi_dung_anh")
    )


def trang_cong_khai():
    return TrangNoiDung.objects.filter(dang_hien_thi=True).defer("noi_dung_trang")


def tin_tuc_cong_khai():
    """Bài đang hiển thị và đã đến giờ đăng, mới nhất trước."""
    return TinTuc.objects.filter(dang_hien_thi=True, thoi_diem_dang__lte=timezone.now())


def nguon_hinh_anh_cong_khai():
    """Nguồn và giấy phép của ảnh đang công khai: thuốc đang bán, chi nhánh hoạt động, banner."""
    from ung_dung.danh_muc.models import AnhChiNhanh, AnhThuoc

    def nhom(tieu_de, cac_dong):
        return {"tieu_de": tieu_de, "cac_dong": [d for d in cac_dong if d["nguon"]]}

    thuoc = (
        AnhThuoc.objects.filter(thuoc__dang_hoat_dong=True)
        .exclude(nguon_anh="")
        .select_related("thuoc")
        .defer("noi_dung_anh")
        .order_by("thuoc__ten_thuoc", "thu_tu", "pk")
    )
    chi_nhanh = (
        AnhChiNhanh.objects.filter(chi_nhanh__dang_hoat_dong=True)
        .exclude(nguon_anh="")
        .select_related("chi_nhanh")
        .defer("noi_dung_anh")
        .order_by("chi_nhanh__ma_chi_nhanh", "thu_tu", "pk")
    )
    return [
        nhom("Ảnh sản phẩm", [{"ten": a.thuoc.ten_thuoc, "nguon": a.nguon_anh} for a in thuoc]),
        nhom(
            "Ảnh nhà thuốc",
            [{"ten": a.chi_nhanh.ten_chi_nhanh, "nguon": a.nguon_anh} for a in chi_nhanh],
        ),
        nhom(
            "Ảnh banner trang chủ",
            [{"ten": b.tieu_de, "nguon": b.nguon_anh} for b in banner_dang_hien()],
        ),
    ]
