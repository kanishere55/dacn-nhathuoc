from django.utils import timezone

from ung_dung.ban_hang.selectors import lay_don
from ung_dung.danh_muc.selectors import lay_chi_nhanh
from ung_dung.du_bao.selectors import lay_ket_qua_moi_nhat
from ung_dung.kho.selectors import lay_canh_bao, lay_canh_bao_ton_thap
from ung_dung.tro_chuyen.selectors import lay_phong_co_tin_moi
from ung_dung.webgis.selectors import lay_tuy_chon_ban_do_nhiet

from .permissions import co_quyen, co_vai_tro, la_quan_tri

SO_DONG_TOM_TAT = 5


def lay_bang_dieu_khien(nguoi):
    # Mỗi khối dữ liệu chỉ nạp khi tài khoản có quyền xem tương ứng.
    quyen = {
        "duoc_xem_kho": co_quyen(nguoi, "ton_kho.xem"),
        "duoc_xem_don": co_quyen(nguoi, "don_hang.xem"),
        "duoc_ban": co_quyen(nguoi, "phieu_ban.tao"),
        "duoc_chat": co_quyen(nguoi, "tro_chuyen.dung"),
        "duoc_xem_bao_cao": co_quyen(nguoi, "bao_cao.xem"),
        "duoc_xem_du_bao": co_quyen(nguoi, "du_bao.xem"),
        "duoc_xem_ban_do_nhiet": co_quyen(nguoi, "ban_do_nhiet.xem"),
    }
    lo_canh_bao = lay_canh_bao(nguoi) if quyen["duoc_xem_kho"] else []
    ton_thap = lay_canh_bao_ton_thap(nguoi) if quyen["duoc_xem_kho"] else []
    don_cho_nhan = lay_don(nguoi).filter(con_hieu_luc=True).order_by("thoi_diem_het_giu", "pk")
    if not quyen["duoc_xem_don"]:
        don_cho_nhan = don_cho_nhan.none()
    noi_dung = {
        **quyen,
        "hom_nay": timezone.localdate(),
        "quan_tri_chuoi": la_quan_tri(nguoi),
        "quan_ly_chi_nhanh": co_vai_tro(nguoi, "quan_ly_chi_nhanh"),
        "so_lo_canh_bao": len(lo_canh_bao),
        "so_canh_bao_ton_thap": len(ton_thap),
        "so_don_cho_nhan": don_cho_nhan.count(),
        "cac_lo_canh_bao": lo_canh_bao[:SO_DONG_TOM_TAT],
        "cac_canh_bao_ton_thap": ton_thap[:SO_DONG_TOM_TAT],
        "cac_don_cho_nhan": list(don_cho_nhan[:SO_DONG_TOM_TAT]),
    }
    if noi_dung["quan_tri_chuoi"]:
        du_bao = lay_ket_qua_moi_nhat()
        noi_dung.update(
            tieu_de="Tổng quan quản trị chuỗi",
            so_chi_nhanh=lay_chi_nhanh(nguoi, ca_chi_nhanh_ngung=True).count(),
            ban_do_nhiet=lay_tuy_chon_ban_do_nhiet(),
            lan_du_bao=du_bao["lan"],
            cac_nhom_du_bao=du_bao.get("cac_nhom", []),
        )
    else:
        cac_phong = (
            lay_phong_co_tin_moi(nguoi)
            if quyen["duoc_chat"]
            else lay_phong_co_tin_moi(nguoi).none()
        )
        noi_dung.update(
            tieu_de=(
                "Tổng quan quản lý chi nhánh"
                if noi_dung["quan_ly_chi_nhanh"]
                else "Tổng quan nhân viên"
            ),
            chi_nhanh=nguoi.chi_nhanh,
            ban_hom_nay=_ban_hom_nay(nguoi) if co_quyen(nguoi, "phieu_ban.xem") else None,
            so_cuoc_co_tin_moi=cac_phong.count(),
            cac_cuoc_co_tin_moi=list(cac_phong[:SO_DONG_TOM_TAT]),
        )
    return noi_dung


def _ban_hom_nay(nguoi):
    """Số phiếu và doanh thu hàng hôm nay của chi nhánh (không tính phiếu đã hoàn kho)."""
    from django.db.models import DecimalField, ExpressionWrapper, F, Sum

    from ung_dung.ban_hang.models import ChiTietPhieuBan, PhieuHoanKho
    from ung_dung.ban_hang.selectors import lay_phieu_ban

    phieu = (
        lay_phieu_ban(nguoi)
        .filter(thoi_diem_tao__date=timezone.localdate())
        .exclude(pk__in=PhieuHoanKho.objects.values("phieu_ban"))
    )
    tien = ExpressionWrapper(F("so_luong") * F("don_gia"), output_field=DecimalField())
    return {
        "so_phieu": phieu.count(),
        "doanh_thu": ChiTietPhieuBan.objects.filter(phieu_ban__in=phieu).aggregate(
            tong=Sum(tien, default=0)
        )["tong"],
    }
