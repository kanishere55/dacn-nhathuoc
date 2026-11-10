"""Bộ lọc cho các danh sách của kho: chứng từ, tồn kho theo lô và lô thuốc."""

from datetime import timedelta

from django.utils import timezone

from ung_dung.chung.loc_danh_sach import BoLoc, OChon, o_khoang_thoi_gian
from ung_dung.chung.permissions import thay_toan_chuoi
from ung_dung.danh_muc.models import DanhMucSanPham, NhomATC
from ung_dung.danh_muc.selectors import lay_chi_nhanh

HAN_DUNG = [
    ("het_han", "Đã hết hạn"),
    ("sap_het_han", "Hết hạn trong 30 ngày"),
    ("con_han", "Còn hạn trên 30 ngày"),
]


def _loc_han_dung(cot):
    def loc(tap_hop, gia_tri):
        hom_nay = timezone.localdate()
        moc = hom_nay + timedelta(days=30)
        if gia_tri == "het_han":
            return tap_hop.filter(**{f"{cot}__lt": hom_nay})
        if gia_tri == "sap_het_han":
            return tap_hop.filter(**{f"{cot}__gte": hom_nay, f"{cot}__lte": moc})
        return tap_hop.filter(**{f"{cot}__gt": moc})

    return loc


def o_chi_nhanh(nguoi, cot):
    """Ô chọn chi nhánh chỉ hiện khi người dùng thấy nhiều hơn một chi nhánh."""
    cac_chi_nhanh = list(lay_chi_nhanh(nguoi, ca_chi_nhanh_ngung=True))
    if len(cac_chi_nhanh) < 2 and not thay_toan_chuoi(nguoi):
        return []
    return [OChon("chi_nhanh", "Chi nhánh", [(c.pk, c.ten_chi_nhanh) for c in cac_chi_nhanh], cot)]


def loc_phieu(request, model, duong_dan_chi_nhanh="chi_nhanh"):
    cot_ma = next(cot.name for cot in model._meta.fields if cot.name.startswith("ma_phieu"))
    return BoLoc(
        request,
        cac_cot_tim=(cot_ma, "nguoi_lap__ten_dang_nhap", "nguoi_lap__ho_ten"),
        nhan_tim="Mã chứng từ, người lập",
        cac_o_chon=[
            *o_chi_nhanh(request.user, f"{duong_dan_chi_nhanh}_id"),
            o_khoang_thoi_gian("thoi_diem_tao"),
        ],
    )


def loc_ton_kho(request):
    return BoLoc(
        request,
        cac_cot_tim=(
            "lo_thuoc__thuoc__ten_thuoc",
            "lo_thuoc__thuoc__ma_thuoc",
            "lo_thuoc__ma_lo_thuoc",
        ),
        nhan_tim="Tên, mã thuốc hoặc mã lô",
        cac_o_chon=[
            *o_chi_nhanh(request.user, "chi_nhanh_id"),
            OChon(
                "danh_muc",
                "Danh mục",
                [(d.pk, d.ten_danh_muc_san_pham) for d in DanhMucSanPham.objects.all()],
                "lo_thuoc__thuoc__danh_muc_san_pham_id",
            ),
            OChon(
                "nhom_atc",
                "Nhóm ATC",
                [(n.pk, n.ma_nhom_atc) for n in NhomATC.objects.all()],
                "lo_thuoc__thuoc__nhom_atc_id",
            ),
            OChon(
                "han_dung", "Hạn dùng", HAN_DUNG, ham_loc=_loc_han_dung("lo_thuoc__ngay_het_han")
            ),
            # Mặc định chỉ hiện lô còn hàng: lô đã về 0 là lịch sử, không cần thấy hằng ngày.
            OChon(
                "con_hang",
                "Tồn",
                [("khong", "Lô đã hết"), ("tat_ca", "Tất cả lô")],
                ham_loc=lambda tap_hop, gia_tri: (
                    tap_hop
                    if gia_tri == "tat_ca"
                    else tap_hop.filter(so_luong=0)
                    if gia_tri == "khong"
                    else tap_hop.filter(so_luong__gt=0)
                ),
                nhan_trong="Còn hàng",
                loc_khi_trong=True,
            ),
        ],
        mac_dinh_moi_trang=50,
    )


def loc_lo_thuoc(request):
    return BoLoc(
        request,
        cac_cot_tim=("ma_lo_thuoc", "thuoc__ten_thuoc", "thuoc__ma_thuoc"),
        nhan_tim="Mã lô, tên hoặc mã thuốc",
        cac_o_chon=[
            OChon("han_dung", "Hạn dùng", HAN_DUNG, ham_loc=_loc_han_dung("ngay_het_han")),
            OChon(
                "dieu_kien_ban",
                "Điều kiện bán",
                [("co", "Cho phép bán"), ("khong", "Ngừng bán")],
                ham_loc=lambda tap_hop, gia_tri: tap_hop.filter(duoc_phep_ban=gia_tri == "co"),
            ),
        ],
    )
