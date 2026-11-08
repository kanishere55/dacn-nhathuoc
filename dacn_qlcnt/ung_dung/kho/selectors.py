from django.apps import apps
from django.db.models import BigIntegerField, Case, F, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from ung_dung.chung.permissions import la_quan_tri

from .models import LoThuoc, TonKho


def lay_so_du(*, nguoi=None, chi_nhanh=None, bo_qua_don=None):
    dang_giu = Value(0)
    if apps.is_installed("ung_dung.ban_hang"):
        from ung_dung.ban_hang.models import TRANG_THAI_GIU

        PhanBoDonHang = apps.get_model("ban_hang", "PhanBoDonHang")
        giu = PhanBoDonHang.objects.filter(
            ton_kho_id=OuterRef("pk"),
            chi_tiet_don_hang__don_hang__trang_thai__in=TRANG_THAI_GIU,
            chi_tiet_don_hang__don_hang__thoi_diem_het_giu__gt=timezone.now(),
        )
        if bo_qua_don:
            giu = giu.exclude(chi_tiet_don_hang__don_hang=bo_qua_don)
        giu = giu.values("ton_kho_id").annotate(tong=Sum("so_luong")).values("tong")
        dang_giu = Coalesce(
            Subquery(giu, output_field=BigIntegerField()), 0, output_field=BigIntegerField()
        )
    tap_hop = (
        TonKho.objects.select_related(
            "chi_nhanh", "lo_thuoc__thuoc__don_vi_tinh", "lo_thuoc__thuoc__nhom_atc"
        )
        .annotate(dang_giu=dang_giu)
        .annotate(kha_dung=F("so_luong") - F("dang_giu"))
    )
    if nguoi is not None and not la_quan_tri(nguoi):
        tap_hop = tap_hop.filter(chi_nhanh_id=nguoi.chi_nhanh_id)
    if chi_nhanh is not None:
        tap_hop = tap_hop.filter(chi_nhanh=chi_nhanh)
    return tap_hop


def dieu_kien_lo_hop_le():
    return Q(
        lo_thuoc__ngay_het_han__gte=timezone.localdate(),
        lo_thuoc__duoc_phep_ban=True,
        lo_thuoc__thuoc__dang_hoat_dong=True,
        chi_nhanh__dang_hoat_dong=True,
    )


def lay_ton_kha_dung(**tham_so):
    return lay_so_du(**tham_so).filter(dieu_kien_lo_hop_le())


def loc_chi_nhanh_du_thuoc(cac_chi_nhanh, cac_dong):
    nhu_cau = {}
    for dong in cac_dong:
        ma = dong["thuoc"].pk
        nhu_cau[ma] = nhu_cau.get(ma, 0) + dong["so_luong"]
    so_du = (
        lay_ton_kha_dung()
        .filter(chi_nhanh__in=cac_chi_nhanh, lo_thuoc__thuoc_id__in=nhu_cau)
        .order_by()
        .values("chi_nhanh_id", "lo_thuoc__thuoc_id")
        .annotate(luong=Sum("kha_dung"))
    )
    bang = {(dong["chi_nhanh_id"], dong["lo_thuoc__thuoc_id"]): dong["luong"] for dong in so_du}
    return [
        cn
        for cn in cac_chi_nhanh
        if all(bang.get((cn.pk, ma), 0) >= luong for ma, luong in nhu_cau.items())
    ]


def lay_bang_ton(nguoi):
    return (
        lay_so_du(nguoi=nguoi)
        .annotate(
            kha_dung_hop_le=Case(
                When(dieu_kien_lo_hop_le(), then=F("kha_dung")),
                default=0,
                output_field=BigIntegerField(),
            )
        )
        .order_by("chi_nhanh__ma_chi_nhanh", "lo_thuoc__ngay_het_han")
    )


def lay_canh_bao_ton_thap(nguoi):
    from ung_dung.danh_muc.models import Thuoc
    from ung_dung.danh_muc.selectors import lay_chi_nhanh

    cac_canh_bao = []
    for chi_nhanh in lay_chi_nhanh(nguoi):
        luong = (
            lay_ton_kha_dung(chi_nhanh=chi_nhanh)
            .filter(lo_thuoc__thuoc_id=OuterRef("pk"))
            .order_by()
            .values("lo_thuoc__thuoc_id")
            .annotate(tong=Sum("kha_dung"))
            .values("tong")
        )
        cac_thuoc = (
            Thuoc.objects.filter(dang_hoat_dong=True, nguong_canh_bao__gt=0)
            .select_related("don_vi_tinh")
            .annotate(
                kha_dung=Coalesce(
                    Subquery(luong, output_field=BigIntegerField()),
                    0,
                    output_field=BigIntegerField(),
                )
            )
            .filter(kha_dung__lt=F("nguong_canh_bao"))
            .order_by("ma_thuoc")
        )
        cac_canh_bao.extend((chi_nhanh, thuoc) for thuoc in cac_thuoc)
    return cac_canh_bao


def lay_canh_bao(nguoi):
    from datetime import timedelta

    cac_dong = list(lay_so_du(nguoi=nguoi).order_by("lo_thuoc__ngay_het_han"))
    hom_nay = timezone.localdate()
    return [
        dong
        for dong in cac_dong
        if dong.so_luong
        and (
            dong.lo_thuoc.ngay_het_han <= hom_nay + timedelta(days=30)
            or not dong.lo_thuoc.duoc_phep_ban
        )
    ]


def lay_phieu(nguoi, model, duong_dan="chi_nhanh"):
    tap_hop = model.objects.all().order_by("-pk")
    if not la_quan_tri(nguoi):
        tap_hop = tap_hop.filter(**{f"{duong_dan}_id": nguoi.chi_nhanh_id})
    return tap_hop


def lay_cac_lo(nguoi):
    cac_lo = LoThuoc.objects.select_related("thuoc").order_by("ngay_het_han", "ma_lo_thuoc")
    if not la_quan_tri(nguoi):
        cac_lo = cac_lo.filter(tonkho__chi_nhanh_id=nguoi.chi_nhanh_id).distinct()
    return cac_lo
