from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Sum

from ung_dung.chung.permissions import kiem_tra_vai_tro
from ung_dung.danh_muc.models import ChiNhanh
from ung_dung.kho.selectors import lay_ton_kha_dung


def tim_chi_nhanh(kinh_do, vi_do, ban_kinh_met, cac_thuoc):
    vi_tri = Point(kinh_do, vi_do, srid=4326)
    cac_chi_nhanh = (
        ChiNhanh.objects.filter(dang_hoat_dong=True, vi_tri__dwithin=(vi_tri, D(m=ban_kinh_met)))
        .annotate(khoang_cach=Distance("vi_tri", vi_tri))
        .order_by("khoang_cach", "ma_chi_nhanh")
    )
    nhu_cau = {}
    for dong in cac_thuoc:
        nhu_cau[dong["thuoc"].pk] = nhu_cau.get(dong["thuoc"].pk, 0) + dong["so_luong"]
    so_du = (
        lay_ton_kha_dung()
        .filter(chi_nhanh__in=cac_chi_nhanh, lo_thuoc__thuoc_id__in=nhu_cau)
        .values("chi_nhanh_id", "lo_thuoc__thuoc_id")
        .annotate(luong=Sum("kha_dung"))
    )
    bang = {(d["chi_nhanh_id"], d["lo_thuoc__thuoc_id"]): d["luong"] for d in so_du}
    ket_qua = []
    for cn in cac_chi_nhanh:
        if all(bang.get((cn.pk, ma), 0) >= luong for ma, luong in nhu_cau.items()):
            ket_qua.append(
                {
                    "id_chi_nhanh": cn.pk,
                    "ma_chi_nhanh": cn.ma_chi_nhanh,
                    "ten_chi_nhanh": cn.ten_chi_nhanh,
                    "dia_chi": cn.dia_chi,
                    "vi_do": cn.vi_tri.y,
                    "kinh_do": cn.vi_tri.x,
                    "khoang_cach_met": round(cn.khoang_cach.m, 1),
                }
            )
        if len(ket_qua) >= 50:
            break
    return ket_qua


def lay_ban_do_nhiet(nguoi, nhom_atc, don_vi_tinh):
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
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
        for cn in ChiNhanh.objects.filter(dang_hoat_dong=True)
    ]
