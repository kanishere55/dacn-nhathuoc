from ung_dung.ban_hang.selectors import lay_don
from ung_dung.danh_muc.selectors import lay_chi_nhanh
from ung_dung.du_bao.selectors import lay_ket_qua_moi_nhat
from ung_dung.kho.selectors import lay_canh_bao, lay_canh_bao_ton_thap
from ung_dung.tro_chuyen.selectors import lay_phong_co_tin_moi
from ung_dung.webgis.selectors import lay_tuy_chon_ban_do_nhiet

from .permissions import co_vai_tro, la_quan_tri

SO_DONG_TOM_TAT = 5


def lay_bang_dieu_khien(nguoi):
    lo_canh_bao = lay_canh_bao(nguoi)
    ton_thap = lay_canh_bao_ton_thap(nguoi)
    don_cho_nhan = lay_don(nguoi).filter(con_hieu_luc=True).order_by("thoi_diem_het_giu", "pk")
    noi_dung = {
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
            cac_du_bao=list(du_bao["cac_du_bao"][:SO_DONG_TOM_TAT]) if du_bao["lan"] else [],
        )
    else:
        cac_phong = lay_phong_co_tin_moi(nguoi)
        noi_dung.update(
            tieu_de=(
                "Tổng quan quản lý chi nhánh"
                if noi_dung["quan_ly_chi_nhanh"]
                else "Tổng quan nhân viên"
            ),
            chi_nhanh=nguoi.chi_nhanh,
            so_cuoc_co_tin_moi=cac_phong.count(),
            cac_cuoc_co_tin_moi=list(cac_phong[:SO_DONG_TOM_TAT]),
        )
    return noi_dung
