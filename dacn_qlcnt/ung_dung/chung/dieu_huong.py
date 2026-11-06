from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

from .permissions import la_quan_tri

DANH_MUC = (
    ("danh_muc:chi_nhanh_danh_sach", "Chi nhánh", "store"),
    ("danh_muc:thuoc_danh_sach", "Thuốc", "pill"),
    ("danh_muc:nhom_atc_danh_sach", "Nhóm ATC", "tags"),
    ("danh_muc:don_vi_tinh_danh_sach", "Đơn vị tính", "ruler"),
    ("danh_muc:quy_doi_bao_goi_danh_sach", "Quy đổi bao gói", "package"),
    ("danh_muc:nha_cung_cap_danh_sach", "Nhà cung cấp", "truck"),
    ("danh_muc:nhan_vien_danh_sach", "Nhân viên", "users"),
)
KHO = (
    ("kho:ton_kho_danh_sach", "Tồn kho", "warehouse"),
    ("kho:phieu_nhap_danh_sach", "Nhập hàng", "package-plus"),
    ("kho:canh_bao", "Cảnh báo", "triangle-alert"),
)
KHO_QUAN_LY = (
    ("kho:lo_thuoc_danh_sach", "Lô thuốc", "calendar"),
    ("kho:phieu_tra_danh_sach", "Trả nhà cung cấp", "package-minus"),
    ("kho:phieu_dieu_chuyen_danh_sach", "Điều chuyển", "repeat"),
    ("kho:phieu_kiem_ke_danh_sach", "Kiểm kê", "clipboard-check"),
)


def dieu_huong(request):
    nguoi = getattr(request, "user", None) or AnonymousUser()
    trang = request.resolver_match.view_name if request.resolver_match else ""
    cac_muc = [("chung:trang_chu", "Tổng quan", "layout-dashboard")]
    vai_tro = nguoi.vai_tro if nguoi.is_authenticated and nguoi.is_active else ""
    quan_tri = la_quan_tri(nguoi)
    nhan_su = vai_tro in {"nhan_vien", "quan_ly_chi_nhanh"}
    quan_ly = vai_tro == "quan_ly_chi_nhanh"
    if not vai_tro or vai_tro == "khach_hang":
        cac_muc.append(("webgis:ban_do", "Tìm chi nhánh", "map-pinned"))
    if quan_tri:
        cac_muc.append(("tai_khoan:danh_sach", "Tài khoản", "user-round"))
    if quan_tri or nhan_su:
        cac_muc.extend(DANH_MUC)
        cac_muc.extend(KHO)
        cac_muc.append(("ban_hang:phieu_ban_danh_sach", "Bán tại quầy", "receipt"))
    if quan_tri or quan_ly:
        cac_muc.extend(KHO_QUAN_LY)
        cac_muc.append(("bao_cao:tong_hop", "Báo cáo", "chart-no-axes-column"))
    if quan_tri or nhan_su or vai_tro == "khach_hang":
        cac_muc.append(("ban_hang:don_dat_giu_danh_sach", "Đơn đặt giữ", "shopping-basket"))
    if nhan_su or vai_tro == "khach_hang":
        cac_muc.append(("tro_chuyen:danh_sach", "Trò chuyện", "messages-square"))
    if quan_tri:
        cac_muc.extend(
            (
                ("webgis:ban_do_nhiet", "Bản đồ nhiệt", "map"),
                ("du_bao:ket_qua", "Dự báo", "chart-line"),
            )
        )
    return {
        "menu_ung_dung": [
            {"duong_dan": reverse(ten), "nhan": nhan, "bieu_tuong": icon, "dang_chon": ten == trang}
            for ten, nhan, icon in cac_muc
        ]
    }
