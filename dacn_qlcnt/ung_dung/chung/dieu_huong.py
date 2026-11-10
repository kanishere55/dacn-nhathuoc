from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

from .permissions import NHAN_SU_CHI_NHANH, co_quyen, co_vai_tro

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
BAN_HANG = (
    ("ban_hang:phieu_ban_danh_sach", "Bán tại quầy", "receipt"),
    ("ban_hang:don_hang_danh_sach", "Đơn hàng", "shopping-basket"),
    ("ban_hang:tra_hang_danh_sach", "Trả hàng", "undo-2"),
    ("ban_hang:xuat_hoa_don_danh_sach", "Hóa đơn công ty", "building-2"),
    ("tro_chuyen:danh_sach", "Trò chuyện", "messages-square"),
)
PHAN_TICH = (
    ("bao_cao:tong_hop", "Báo cáo", "chart-no-axes-column"),
    ("webgis:ban_do_nhiet", "Bản đồ nhiệt", "map"),
    ("du_bao:ket_qua", "Dự báo", "chart-line"),
)
WEBSITE = (
    ("noi_dung:banner_danh_sach", "Banner trang chủ", "gallery-horizontal"),
    ("noi_dung:trang_danh_sach", "Trang thông tin", "file-text"),
    ("noi_dung:tin_tuc_danh_sach", "Tin tức", "newspaper"),
    ("noi_dung:thong_tin", "Thông tin cửa hàng", "store"),
    ("thong_bao:nhat_ky_email", "Email hệ thống", "mail"),
)
# Mục menu chỉ hiện khi tài khoản có quyền xem tương ứng.
QUYEN_MENU = {
    "danh_muc:chi_nhanh_danh_sach": "chi_nhanh.xem",
    "danh_muc:thuoc_danh_sach": "thuoc.xem",
    "danh_muc:danh_muc_san_pham_danh_sach": "danh_muc_san_pham.xem",
    "danh_muc:khuyen_mai_danh_sach": "khuyen_mai.xem",
    "danh_muc:nhom_atc_danh_sach": "nhom_atc.xem",
    "danh_muc:don_vi_tinh_danh_sach": "don_vi_tinh.xem",
    "danh_muc:quy_doi_bao_goi_danh_sach": "quy_doi_bao_goi.xem",
    "danh_muc:nha_cung_cap_danh_sach": "nha_cung_cap.xem",
    "danh_muc:nhan_vien_danh_sach": "nhan_vien.xem",
    "danh_muc:danh_gia_danh_sach": "danh_gia.xem",
    "kho:ton_kho_danh_sach": "ton_kho.xem",
    "kho:canh_bao": "ton_kho.xem",
    "kho:phieu_nhap_danh_sach": "phieu_nhap.xem",
    "kho:lo_thuoc_danh_sach": "lo_thuoc.xem",
    "kho:phieu_tra_danh_sach": "phieu_tra.xem",
    "kho:phieu_dieu_chuyen_danh_sach": "dieu_chuyen.xem",
    "kho:phieu_kiem_ke_danh_sach": "kiem_ke.xem",
    "kho:phieu_xuat_huy_danh_sach": "xuat_huy.xem",
    "ban_hang:phieu_ban_danh_sach": "phieu_ban.xem",
    "ban_hang:don_hang_danh_sach": "don_hang.xem",
    "ban_hang:tra_hang_danh_sach": "tra_hang.xem",
    "ban_hang:xuat_hoa_don_danh_sach": "hoa_don_cong_ty.xem",
    "tro_chuyen:danh_sach": "tro_chuyen.dung",
    "bao_cao:tong_hop": "bao_cao.xem",
    "webgis:ban_do_nhiet": "ban_do_nhiet.xem",
    "du_bao:ket_qua": "du_bao.xem",
    "noi_dung:banner_danh_sach": "banner.sua",
    "noi_dung:trang_danh_sach": "trang.sua",
    "noi_dung:tin_tuc_danh_sach": "tin_tuc.sua",
    "noi_dung:thong_tin": "thong_tin.sua",
    "thong_bao:nhat_ky_email": "email.xem",
    "tai_khoan:danh_sach": "tai_khoan.xem",
    "tai_khoan:nhom_quyen_danh_sach": "phan_quyen.quan_ly",
}
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


# Nhân viên quầy chỉ cần tra cứu thuốc; các danh mục cấu hình vẫn mở được theo quyền
# nhưng không hiện trên menu để menu chỉ còn việc hằng ngày.
AN_VOI_NHAN_VIEN = {
    "danh_muc:chi_nhanh_danh_sach",
    "danh_muc:danh_muc_san_pham_danh_sach",
    "danh_muc:khuyen_mai_danh_sach",
    "danh_muc:nhom_atc_danh_sach",
    "danh_muc:don_vi_tinh_danh_sach",
    "danh_muc:quy_doi_bao_goi_danh_sach",
    "danh_muc:nha_cung_cap_danh_sach",
    "danh_muc:nhan_vien_danh_sach",
}
# Nhóm ít dùng: thu gọn mặc định, tự mở khi đang ở một trang trong nhóm.
NHOM_THU_GON = {"Danh mục", "Website"}

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
        (
            *(ten for ten, _, _ in DANH_MUC),
            "danh_muc:danh_gia_danh_sach",
            "tai_khoan:danh_sach",
            "tai_khoan:nhom_quyen_danh_sach",
        ),
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
            dang_chon = any(m["dang_chon"] for m in muc)
            ket_qua.append(
                {
                    "nhan": nhan,
                    "cac_muc": muc,
                    "dang_mo": dang_chon,
                    "mo_san": dang_chon or nhan not in NHOM_THU_GON or len(muc) <= 2,
                }
            )
    con_lai = [m for m in cac_muc if m["ten"] not in da_xep]
    if con_lai:
        ket_qua.append({"nhan": "Khác", "cac_muc": con_lai, "dang_mo": False, "mo_san": True})
    return ket_qua


def dieu_huong(request):
    nguoi = getattr(request, "user", None) or AnonymousUser()
    ket_qua = getattr(request, "resolver_match", None)
    trang = ket_qua.view_name if ket_qua else ""
    noi_bo = co_vai_tro(nguoi, "quan_tri_chuoi", *NHAN_SU_CHI_NHANH)
    cac_muc = []
    if noi_bo:
        cac_muc = [
            (ten, nhan, icon)
            for ten, nhan, icon in (
                ("chung:bang_dieu_khien", "Tổng quan", "layout-dashboard"),
                *DANH_MUC,
                *KHO,
                *KHO_QUAN_LY,
                *BAN_HANG,
                *PHAN_TICH,
                *WEBSITE,
                ("tai_khoan:danh_sach", "Tài khoản", "user-round"),
                ("tai_khoan:nhom_quyen_danh_sach", "Nhóm quyền", "shield-check"),
            )
            if (ten not in QUYEN_MENU or co_quyen(nguoi, QUYEN_MENU[ten]))
            and not (nguoi.vai_tro == "nhan_vien" and ten in AN_VOI_NHAN_VIEN)
        ]
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
                    "duong_dan": reverse(
                        "ban_hang:phieu_ban_tao"
                        if ten == "ban_hang:phieu_ban_danh_sach"
                        and co_quyen(nguoi, "phieu_ban.tao")
                        else ten
                    ),
                    "nhan": nhan,
                    "bieu_tuong": icon,
                    "dang_chon": ten == trang
                    or (
                        ten.endswith("_danh_sach")
                        and trang.startswith(ten[:-9])
                        and not (ten == "tai_khoan:danh_sach" and "nhom_quyen" in trang)
                    ),
                }
                for ten, nhan, icon in cac_muc
            ]
        ),
        "menu_nhom": nhom_menu(menu),
    }
