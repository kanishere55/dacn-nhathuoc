"""Điều hướng dùng chung: menu khu quản lý theo quyền, menu website khách, khung trang cho trang lỗi.

Nguồn duy nhất của menu khu quản lý là MUC_MENU: mỗi dòng khai báo tên URL, nhãn, biểu tượng, quyền
cần có và nhóm hiển thị. QUYEN_MENU và NHOM_MENU được sinh từ đây nên ba danh sách không thể lệch nhau
(lỗi cũ QT-01: trang Đánh giá có quyền và nhóm nhưng không có mục menu).
"""

from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.utils.functional import SimpleLazyObject

from .permissions import NHAN_SU_CHI_NHANH, co_quyen, co_vai_tro

# Nhóm menu theo việc của người dùng, theo đúng thứ tự hiện trên thanh bên.
# "" là nhóm không tiêu đề (Tổng quan đứng đầu).
CAC_NHOM = ("", "Bán hàng", "Kho", "Danh mục", "Báo cáo", "Website", "Hệ thống")

# Nhóm ít dùng: thu gọn mặc định, tự mở khi đang ở một trang trong nhóm.
NHOM_THU_GON = {"Danh mục", "Website", "Hệ thống"}

# (tên URL, nhãn, biểu tượng Lucide, mã quyền cần có hoặc None, nhóm, ẩn với nhân viên quầy)
# Nhân viên quầy chỉ cần tra cứu thuốc; các danh mục cấu hình vẫn mở được theo quyền
# nhưng không hiện trên menu để menu chỉ còn việc hằng ngày.
MUC_MENU = (
    ("chung:bang_dieu_khien", "Tổng quan", "layout-dashboard", None, "", False),
    # Bán hàng
    ("ban_hang:phieu_ban_danh_sach", "Bán tại quầy", "receipt", "phieu_ban.xem", "Bán hàng", False),
    (
        "ban_hang:don_hang_danh_sach",
        "Đơn hàng",
        "shopping-basket",
        "don_hang.xem",
        "Bán hàng",
        False,
    ),
    ("ban_hang:tra_hang_danh_sach", "Trả hàng", "undo-2", "tra_hang.xem", "Bán hàng", False),
    (
        "ban_hang:xuat_hoa_don_danh_sach",
        "Hóa đơn công ty",
        "building-2",
        "hoa_don_cong_ty.xem",
        "Bán hàng",
        False,
    ),
    ("tro_chuyen:danh_sach", "Trò chuyện", "messages-square", "tro_chuyen.dung", "Bán hàng", False),
    # Kho
    ("kho:ton_kho_danh_sach", "Tồn kho", "warehouse", "ton_kho.xem", "Kho", False),
    ("kho:canh_bao", "Cảnh báo kho", "triangle-alert", "ton_kho.xem", "Kho", False),
    ("kho:phieu_nhap_danh_sach", "Nhập hàng", "package-plus", "phieu_nhap.xem", "Kho", False),
    ("kho:lo_thuoc_danh_sach", "Lô thuốc", "calendar", "lo_thuoc.xem", "Kho", False),
    ("kho:phieu_dieu_chuyen_danh_sach", "Điều chuyển", "repeat", "dieu_chuyen.xem", "Kho", False),
    ("kho:phieu_kiem_ke_danh_sach", "Kiểm kê", "clipboard-check", "kiem_ke.xem", "Kho", False),
    ("kho:phieu_tra_danh_sach", "Trả nhà cung cấp", "package-minus", "phieu_tra.xem", "Kho", False),
    ("kho:phieu_xuat_huy_danh_sach", "Xuất hủy", "trash-2", "xuat_huy.xem", "Kho", False),
    # Danh mục
    ("danh_muc:thuoc_danh_sach", "Thuốc", "pill", "thuoc.xem", "Danh mục", False),
    ("danh_muc:chi_nhanh_danh_sach", "Chi nhánh", "store", "chi_nhanh.xem", "Danh mục", True),
    (
        "danh_muc:danh_muc_san_pham_danh_sach",
        "Danh mục sản phẩm",
        "layout-list",
        "danh_muc_san_pham.xem",
        "Danh mục",
        True,
    ),
    (
        "danh_muc:khuyen_mai_danh_sach",
        "Khuyến mãi",
        "badge-percent",
        "khuyen_mai.xem",
        "Danh mục",
        True,
    ),
    ("danh_muc:nhom_atc_danh_sach", "Nhóm ATC", "tags", "nhom_atc.xem", "Danh mục", True),
    ("danh_muc:don_vi_tinh_danh_sach", "Đơn vị tính", "ruler", "don_vi_tinh.xem", "Danh mục", True),
    (
        "danh_muc:quy_doi_bao_goi_danh_sach",
        "Quy đổi bao gói",
        "package",
        "quy_doi_bao_goi.xem",
        "Danh mục",
        True,
    ),
    (
        "danh_muc:nha_cung_cap_danh_sach",
        "Nhà cung cấp",
        "truck",
        "nha_cung_cap.xem",
        "Danh mục",
        True,
    ),
    ("danh_muc:nhan_vien_danh_sach", "Nhân viên", "users", "nhan_vien.xem", "Danh mục", True),
    # Báo cáo
    (
        "bao_cao:tong_hop",
        "Báo cáo tổng hợp",
        "chart-no-axes-column",
        "bao_cao.xem",
        "Báo cáo",
        False,
    ),
    ("webgis:ban_do_nhiet", "Bản đồ nhiệt", "map", "ban_do_nhiet.xem", "Báo cáo", False),
    ("du_bao:ket_qua", "Dự báo", "chart-line", "du_bao.xem", "Báo cáo", False),
    # Website
    (
        "noi_dung:banner_danh_sach",
        "Banner trang chủ",
        "gallery-horizontal",
        "banner.sua",
        "Website",
        False,
    ),
    ("noi_dung:trang_danh_sach", "Trang thông tin", "file-text", "trang.sua", "Website", False),
    ("noi_dung:tin_tuc_danh_sach", "Tin tức", "newspaper", "tin_tuc.sua", "Website", False),
    ("danh_muc:danh_gia_danh_sach", "Đánh giá của khách", "star", "danh_gia.xem", "Website", False),
    ("noi_dung:thong_tin", "Thông tin cửa hàng", "info", "thong_tin.sua", "Website", False),
    # Hệ thống
    ("tai_khoan:danh_sach", "Tài khoản", "user-round", "tai_khoan.xem", "Hệ thống", False),
    (
        "tai_khoan:nhom_quyen_danh_sach",
        "Nhóm quyền",
        "shield-check",
        "phan_quyen.quan_ly",
        "Hệ thống",
        False,
    ),
    ("thong_bao:nhat_ky_email", "Email hệ thống", "mail", "email.xem", "Hệ thống", False),
)

# Sinh từ MUC_MENU (giữ tên cũ cho mã và test đang dùng).
QUYEN_MENU = {ten: quyen for ten, _, _, quyen, _, _ in MUC_MENU if quyen}
AN_VOI_NHAN_VIEN = {ten for ten, *_, an in MUC_MENU if an}
NHOM_MENU = tuple(
    (nhom, tuple(ten for ten, _, _, _, n, _ in MUC_MENU if n == nhom)) for nhom in CAC_NHOM
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
# Mục chỉ hiện khi có nội dung, tránh dẫn khách tới trang rỗng (F16).
MENU_KHACH_CAN_NOI_DUNG = {"noi_dung:khach_tin_tuc_danh_sach"}


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


def _dang_chon(ten, trang):
    """Mục menu sáng khi đang ở chính trang đó hoặc trang con cùng tiền tố (…_danh_sach → …_tao, …_sua)."""
    if ten == trang:
        return True
    if not ten.endswith("_danh_sach") or not trang.startswith(ten.removesuffix("danh_sach")):
        return False
    return not (ten == "tai_khoan:danh_sach" and "nhom_quyen" in trang)


def _menu_khach(trang):
    def tao():
        from ung_dung.noi_dung.selectors import tin_tuc_cong_khai

        co_noi_dung = {"noi_dung:khach_tin_tuc_danh_sach": tin_tuc_cong_khai().exists}
        return [
            {"duong_dan": reverse(ten), "nhan": nhan, "dang_chon": trang in cac_trang}
            for ten, nhan, cac_trang in MENU_KHACH
            if ten not in MENU_KHACH_CAN_NOI_DUNG or trang in cac_trang or co_noi_dung[ten]()
        ]

    # Chỉ truy vấn khi template khách thật sự vẽ menu (trang khu quản lý không tốn truy vấn này).
    return SimpleLazyObject(tao)


def dieu_huong(request):
    nguoi = getattr(request, "user", None) or AnonymousUser()
    ket_qua = getattr(request, "resolver_match", None)
    trang = ket_qua.view_name if ket_qua else ""
    noi_bo = co_vai_tro(nguoi, "quan_tri_chuoi", *NHAN_SU_CHI_NHANH)
    cac_muc = []
    if noi_bo:
        cac_muc = [
            (ten, nhan, icon)
            for ten, nhan, icon, quyen, _, an in MUC_MENU
            if (not quyen or co_quyen(nguoi, quyen)) and not (an and nguoi.vai_tro == "nhan_vien")
        ]
    menu = [
        {
            "ten": ten,
            "duong_dan": reverse(
                "ban_hang:phieu_ban_tao"
                if ten == "ban_hang:phieu_ban_danh_sach" and co_quyen(nguoi, "phieu_ban.tao")
                else ten
            ),
            "nhan": nhan,
            "bieu_tuong": icon,
            "dang_chon": _dang_chon(ten, trang),
        }
        for ten, nhan, icon in cac_muc
    ]
    cac_nhom = nhom_menu(menu)
    nhom_dang_chon = next((n["nhan"] for n in cac_nhom if n["dang_mo"]), "")
    phien = getattr(request, "session", None)
    duong_dan = getattr(request, "path", "") or ""
    return {
        "noi_bo": noi_bo,
        # Trang lỗi 403/404 chọn khung theo khu: nhân sự ở /quan-ly/ thấy khung khu quản lý (QT-08).
        "khung_theo_khu": (
            "base.html" if noi_bo and duong_dan.startswith("/quan-ly/") else "khach/base.html"
        ),
        "so_mon_gio": len(phien.get("gio_hang", {})) if phien is not None and not noi_bo else 0,
        "menu_khach": _menu_khach(trang),
        "menu_ung_dung": menu,
        "menu_nhom": cac_nhom,
        "nhom_dang_chon": nhom_dang_chon,
        **_thong_bao_tro_chuyen(nguoi, noi_bo, menu),
    }


def _thong_bao_tro_chuyen(nguoi, noi_bo, menu):
    """Huy hiệu tin chưa đọc lấy từ CSDL mỗi lần tải trang; WebSocket chỉ cập nhật tức thời."""
    from ung_dung.tro_chuyen.selectors import dem_chua_doc

    bat = getattr(nguoi, "is_authenticated", False) and (
        nguoi.vai_tro == "khach_hang" or (noi_bo and co_quyen(nguoi, "tro_chuyen.dung"))
    )
    so = dem_chua_doc(nguoi) if bat else 0
    # Mục Trò chuyện trên menu nhân sự hiện số tin khách gửi mà nhà thuốc chưa xem.
    for muc in menu:
        if muc["ten"] == "tro_chuyen:danh_sach":
            muc["co_dem"], muc["so"] = True, so
    return {"bat_thong_bao": bat, "so_tin_chua_doc": so}
