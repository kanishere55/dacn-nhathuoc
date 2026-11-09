from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

from .permissions import NHAN_SU_CHI_NHANH, co_vai_tro, la_quan_tri

DANH_MUC = (
    ("danh_muc:chi_nhanh_danh_sach", "Chi nhánh", "store"),
    ("danh_muc:thuoc_danh_sach", "Thuốc", "pill"),
    ("danh_muc:danh_muc_san_pham_danh_sach", "Danh mục sản phẩm", "layout-list"),
    ("danh_muc:khuyen_mai_danh_sach", "Khuyến mãi", "badge-percent"),
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
    ("kho:phieu_xuat_huy_danh_sach", "Xuất hủy", "trash-2"),
)
MENU_KHACH = (
    ("chung:trang_chu", "Trang chủ", ("chung:trang_chu",)),
    (
        "danh_muc:khach_thuoc_danh_sach",
        "Tra cứu thuốc",
        ("danh_muc:khach_thuoc_danh_sach", "danh_muc:khach_thuoc_chi_tiet"),
    ),
    ("webgis:ban_do", "Tìm nhà thuốc", ("webgis:ban_do", "danh_muc:khach_chi_nhanh_chi_tiet")),
    (
        "noi_dung:khach_tin_tuc_danh_sach",
        "Tin tức",
        ("noi_dung:khach_tin_tuc_danh_sach", "noi_dung:khach_tin_tuc_chi_tiet"),
    ),
)


# Nhóm menu quản lý theo nghiệp vụ; mục không thuộc nhóm nào xếp vào "Khác".
NHOM_MENU = (
    ("", ("chung:bang_dieu_khien",)),
    (
        "Bán hàng",
        (
            "ban_hang:don_hang_danh_sach",
            "ban_hang:tra_hang_danh_sach",
            "ban_hang:xuat_hoa_don_danh_sach",
            "ban_hang:phieu_ban_danh_sach",
            "tro_chuyen:danh_sach",
        ),
    ),
    ("Kho", tuple(ten for ten, _, _ in (*KHO, *KHO_QUAN_LY))),
    (
        "Danh mục",
        (*(ten for ten, _, _ in DANH_MUC), "danh_muc:danh_gia_danh_sach", "tai_khoan:danh_sach"),
    ),
    ("Phân tích", ("bao_cao:tong_hop", "webgis:ban_do_nhiet", "du_bao:ket_qua")),
    (
        "Website",
        (
            "noi_dung:banner_danh_sach",
            "noi_dung:trang_danh_sach",
            "noi_dung:tin_tuc_danh_sach",
            "noi_dung:thong_tin",
            "thong_bao:nhat_ky_email",
        ),
    ),
)


def nhom_menu(cac_muc):
    theo_ten = {muc["ten"]: muc for muc in cac_muc}
    ket_qua, da_xep = [], set()
    for nhan, cac_ten in NHOM_MENU:
        muc = [theo_ten[ten] for ten in cac_ten if ten in theo_ten]
        da_xep.update(m["ten"] for m in muc)
        if muc:
            ket_qua.append(
                {"nhan": nhan, "cac_muc": muc, "dang_mo": any(m["dang_chon"] for m in muc)}
            )
    con_lai = [m for m in cac_muc if m["ten"] not in da_xep]
    if con_lai:
        ket_qua.append({"nhan": "Khác", "cac_muc": con_lai, "dang_mo": False})
    return ket_qua


def dieu_huong(request):
    nguoi = getattr(request, "user", None) or AnonymousUser()
    ket_qua = getattr(request, "resolver_match", None)
    trang = ket_qua.view_name if ket_qua else ""
    quan_tri = la_quan_tri(nguoi)
    nhan_su = co_vai_tro(nguoi, *NHAN_SU_CHI_NHANH)
    quan_ly = co_vai_tro(nguoi, "quan_ly_chi_nhanh")
    noi_bo = quan_tri or nhan_su
    cac_muc = [("chung:bang_dieu_khien", "Tổng quan", "layout-dashboard")] if noi_bo else []
    if quan_tri:
        cac_muc.append(("tai_khoan:danh_sach", "Tài khoản", "user-round"))
    if noi_bo:
        cac_muc.extend(DANH_MUC)
        cac_muc.extend(KHO)
        cac_muc.append(("ban_hang:phieu_ban_danh_sach", "Bán tại quầy", "receipt"))
    if quan_tri:
        cac_muc.append(("danh_muc:danh_gia_danh_sach", "Đánh giá", "star"))
    if quan_tri or quan_ly:
        cac_muc.extend(KHO_QUAN_LY)
        cac_muc.append(("bao_cao:tong_hop", "Báo cáo", "chart-no-axes-column"))
    if noi_bo:
        cac_muc.append(("ban_hang:don_hang_danh_sach", "Đơn hàng", "shopping-basket"))
        cac_muc.append(("ban_hang:tra_hang_danh_sach", "Trả hàng", "undo-2"))
        cac_muc.append(("ban_hang:xuat_hoa_don_danh_sach", "Hóa đơn công ty", "building-2"))
    if nhan_su:
        cac_muc.append(("tro_chuyen:danh_sach", "Trò chuyện", "messages-square"))
    if quan_tri:
        cac_muc.extend(
            (
                ("webgis:ban_do_nhiet", "Bản đồ nhiệt", "map"),
                ("du_bao:ket_qua", "Dự báo", "chart-line"),
                ("thong_bao:nhat_ky_email", "Email hệ thống", "mail"),
                ("noi_dung:banner_danh_sach", "Banner trang chủ", "gallery-horizontal"),
                ("noi_dung:trang_danh_sach", "Trang thông tin", "file-text"),
                ("noi_dung:tin_tuc_danh_sach", "Tin tức", "newspaper"),
                ("noi_dung:thong_tin", "Thông tin cửa hàng", "store"),
            )
        )
    phien = getattr(request, "session", None)
    return {
        "noi_bo": noi_bo,
        "so_mon_gio": len(phien.get("gio_hang", {})) if phien is not None and not noi_bo else 0,
        "menu_khach": [
            {"duong_dan": reverse(ten), "nhan": nhan, "dang_chon": trang in cac_trang}
            for ten, nhan, cac_trang in MENU_KHACH
        ],
        "menu_ung_dung": (
            menu := [
                {
                    "ten": ten,
                    "duong_dan": reverse(ten),
                    "nhan": nhan,
                    "bieu_tuong": icon,
                    "dang_chon": ten == trang
                    or (ten.endswith("_danh_sach") and trang.startswith(ten[:-9])),
                }
                for ten, nhan, icon in cac_muc
            ]
        ),
        "menu_nhom": nhom_menu(menu),
    }
