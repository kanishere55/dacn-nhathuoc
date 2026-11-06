from django.db.models import F

from .models import DuBaoBayNgay, KetQuaMoHinh, KichBanThieuHang, LanThucNghiem


def lay_ket_qua_moi_nhat():
    lan = LanThucNghiem.objects.select_related("nguon_du_lieu").order_by("-pk").first()
    if lan is None:
        return {"lan": None}
    return {
        "lan": lan,
        "cac_mo_hinh": KetQuaMoHinh.objects.filter(lan_thuc_nghiem=lan).order_by(
            "ma_atc_nguon", "-duoc_chon", "mae_xac_thuc"
        ),
        "cac_du_bao": DuBaoBayNgay.objects.filter(
            ket_qua_mo_hinh__lan_thuc_nghiem=lan, ky_danh_gia="tuong_lai"
        )
        .select_related("ket_qua_mo_hinh")
        .order_by("ket_qua_mo_hinh__ma_atc_nguon"),
        "cac_kich_ban": KichBanThieuHang.objects.filter(
            du_bao_bay_ngay__ket_qua_mo_hinh__lan_thuc_nghiem=lan
        )
        .select_related("du_bao_bay_ngay__ket_qua_mo_hinh")
        .annotate(
            kha_dung=F("so_luong_ton") - F("so_luong_dang_giu"),
            chenh_lech=F("so_luong_ton")
            - F("so_luong_dang_giu")
            - F("so_luong_du_tru")
            - F("du_bao_bay_ngay__so_luong_du_bao"),
        )
        .order_by("-pk")[:20],
    }
