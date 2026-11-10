from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Sum
from django.urls import reverse

from ung_dung.chung.permissions import kiem_tra_quyen
from ung_dung.danh_muc.models import ChiNhanh, DonViTinh, NhomATC
from ung_dung.danh_muc.selectors import lay_chi_nhanh, lay_thuoc_cong_khai
from ung_dung.kho.selectors import lay_ton_kha_dung, loc_chi_nhanh_du_thuoc


def lay_chi_nhanh_ban_do(kinh_do=None, vi_do=None, ban_kinh_met=None):
    """Mọi chi nhánh đang hoạt động cho trang tìm nhà thuốc.

    Có tọa độ người xem thì PostGIS tính khoảng cách (ST_Distance), lọc bán kính bằng ST_DWithin
    và sắp gần nhất trước; chưa có tọa độ thì sắp theo mã.
    """
    from django.db.models import Avg, Count, OuterRef, Q, Subquery
    from django.utils import timezone

    from ung_dung.danh_muc.models import AnhChiNhanh

    anh_dau = AnhChiNhanh.objects.filter(chi_nhanh=OuterRef("pk")).order_by("thu_tu", "pk")
    tap_hop = ChiNhanh.objects.filter(dang_hoat_dong=True).annotate(
        id_anh=Subquery(anh_dau.values("pk")[:1]),
        diem_sao=Avg("cac_danh_gia__so_sao", filter=Q(cac_danh_gia__dang_hien_thi=True)),
        so_danh_gia=Count("cac_danh_gia", filter=Q(cac_danh_gia__dang_hien_thi=True)),
    )
    co_vi_tri = kinh_do is not None and vi_do is not None
    if co_vi_tri:
        vi_tri = Point(kinh_do, vi_do, srid=4326)
        tap_hop = tap_hop.annotate(khoang_cach=Distance("vi_tri", vi_tri))
        if ban_kinh_met:
            tap_hop = tap_hop.filter(vi_tri__dwithin=(vi_tri, D(m=ban_kinh_met)))
        tap_hop = tap_hop.order_by("khoang_cach", "ma_chi_nhanh")
    else:
        tap_hop = tap_hop.order_by("ma_chi_nhanh")
    bay_gio = timezone.localtime().time()
    return [
        {
            "id_chi_nhanh": cn.pk,
            "ma_chi_nhanh": cn.ma_chi_nhanh,
            "ten_chi_nhanh": cn.ten_chi_nhanh,
            "dia_chi": cn.dia_chi,
            "so_dien_thoai": cn.so_dien_thoai,
            "gio_mo_cua": cn.gio_mo_cua.strftime("%H:%M"),
            "gio_dong_cua": cn.gio_dong_cua.strftime("%H:%M"),
            "dang_mo_cua": cn.gio_mo_cua <= bay_gio < cn.gio_dong_cua,
            "vi_do": cn.vi_tri.y,
            "kinh_do": cn.vi_tri.x,
            "khoang_cach_met": round(cn.khoang_cach.m, 1) if co_vi_tri else None,
            "diem_sao": round(cn.diem_sao, 1) if cn.diem_sao else None,
            "so_danh_gia": cn.so_danh_gia,
            "anh": reverse("danh_muc:anh_chi_nhanh", args=[cn.id_anh]) if cn.id_anh else "",
            "duong_dan": reverse("danh_muc:khach_chi_nhanh_chi_tiet", args=[cn.ma_chi_nhanh]),
        }
        for cn in tap_hop[:100]
    ]


def tim_chi_nhanh(kinh_do, vi_do, ban_kinh_met, cac_thuoc):
    vi_tri = Point(kinh_do, vi_do, srid=4326)
    cac_chi_nhanh = (
        ChiNhanh.objects.filter(dang_hoat_dong=True, vi_tri__dwithin=(vi_tri, D(m=ban_kinh_met)))
        .annotate(khoang_cach=Distance("vi_tri", vi_tri))
        .order_by("khoang_cach", "ma_chi_nhanh")
    )
    return [
        {
            "id_chi_nhanh": cn.pk,
            "ma_chi_nhanh": cn.ma_chi_nhanh,
            "ten_chi_nhanh": cn.ten_chi_nhanh,
            "dia_chi": cn.dia_chi,
            "vi_do": cn.vi_tri.y,
            "kinh_do": cn.vi_tri.x,
            "khoang_cach_met": round(cn.khoang_cach.m, 1),
            "duong_dan": reverse("danh_muc:khach_chi_nhanh_chi_tiet", args=[cn.ma_chi_nhanh]),
        }
        for cn in loc_chi_nhanh_du_thuoc(cac_chi_nhanh, cac_thuoc)[:50]
    ]


def lay_tuy_chon_ban_do_nhiet():
    mac_dinh = lay_thuoc_cong_khai().values_list("nhom_atc_id", "don_vi_tinh_id").first()
    return {
        "cac_nhom": list(NhomATC.objects.order_by("ma_nhom_atc")),
        "cac_don_vi": list(DonViTinh.objects.order_by("ma_don_vi_tinh")),
        "id_nhom_mac_dinh": mac_dinh[0] if mac_dinh else None,
        "id_don_vi_mac_dinh": mac_dinh[1] if mac_dinh else None,
    }


def lay_ban_do_nhiet(nguoi, nhom_atc, don_vi_tinh):
    kiem_tra_quyen(nguoi, "ban_do_nhiet.xem")
    so_du = (
        lay_ton_kha_dung()
        .filter(lo_thuoc__thuoc__nhom_atc=nhom_atc, lo_thuoc__thuoc__don_vi_tinh=don_vi_tinh)
        .values("chi_nhanh_id")
        .annotate(luong=Sum("kha_dung"))
    )
    cac_luong = {dong["chi_nhanh_id"]: dong["luong"] for dong in so_du}
    return [
        {
            "ten_chi_nhanh": cn.ten_chi_nhanh,
            "vi_do": cn.vi_tri.y,
            "kinh_do": cn.vi_tri.x,
            "so_luong": cac_luong.get(cn.pk, 0),
        }
        for cn in lay_chi_nhanh(nguoi, ca_chi_nhanh_ngung=True)
    ]
