"""Danh mục quyền chi tiết của khu quản lý và quyền mặc định của từng vai trò.

Mỗi quyền là một mã `nhóm.hành_động`. Quản trị chuỗi luôn có mọi quyền và không bị giới hạn.
Quản lý chi nhánh và nhân viên nhận quyền từ nhóm quyền được gán (hoặc nhóm mặc định của vai
trò), sau đó từng quyền riêng của tài khoản có thể cho thêm hoặc chặn bớt.

Quyền đánh dấu `chi_quan_tri` (tài khoản, phân quyền, dữ liệu mô phỏng) không giao cho người
khác được, để không ai tự nâng quyền của mình.
"""

from dataclasses import dataclass

QUAN_TRI = "quan_tri_chuoi"
QUAN_LY = "quan_ly_chi_nhanh"
NHAN_VIEN = "nhan_vien"


@dataclass(frozen=True)
class Quyen:
    ma: str
    nhom: str
    nhan: str
    mo_ta: str = ""
    chi_quan_tri: bool = False


def _q(nhom, *cac_quyen):
    return [Quyen(ma, nhom, nhan, *phan_con) for ma, nhan, *phan_con in cac_quyen]


DANH_SACH_QUYEN = [
    *_q(
        "Phạm vi dữ liệu",
        (
            "pham_vi.toan_chuoi",
            "Xem và thao tác trên mọi chi nhánh",
            "Không bị giới hạn ở chi nhánh được phân công.",
        ),
    ),
    *_q(
        "Danh mục",
        ("chi_nhanh.xem", "Xem chi nhánh"),
        ("chi_nhanh.sua", "Thêm, sửa chi nhánh và ảnh chi nhánh"),
        ("thuoc.xem", "Xem thuốc"),
        ("thuoc.sua", "Thêm, sửa thuốc, nội dung và ảnh thuốc"),
        ("danh_muc_san_pham.xem", "Xem danh mục sản phẩm"),
        ("danh_muc_san_pham.sua", "Thêm, sửa danh mục sản phẩm"),
        ("khuyen_mai.xem", "Xem khuyến mãi"),
        ("khuyen_mai.sua", "Thêm, sửa, dừng khuyến mãi"),
        ("nhom_atc.xem", "Xem nhóm ATC"),
        ("nhom_atc.sua", "Thêm, sửa nhóm ATC"),
        ("don_vi_tinh.xem", "Xem đơn vị tính"),
        ("don_vi_tinh.sua", "Thêm, sửa đơn vị tính"),
        ("quy_doi_bao_goi.xem", "Xem quy đổi bao gói"),
        ("quy_doi_bao_goi.sua", "Thêm, sửa quy đổi bao gói"),
        ("nha_cung_cap.xem", "Xem nhà cung cấp"),
        ("nha_cung_cap.sua", "Thêm, sửa nhà cung cấp"),
        ("nhan_vien.xem", "Xem hồ sơ nhân viên"),
        ("nhan_vien.sua", "Thêm, sửa hồ sơ nhân viên"),
        ("danh_gia.xem", "Xem đánh giá của khách"),
        ("danh_gia.kiem_duyet", "Ẩn hoặc hiện đánh giá"),
    ),
    *_q(
        "Kho",
        ("ton_kho.xem", "Xem tồn kho và cảnh báo"),
        ("lo_thuoc.xem", "Xem lô thuốc"),
        ("lo_thuoc.sua", "Đổi điều kiện bán của lô (cần thêm phạm vi toàn chuỗi)"),
        ("phieu_nhap.xem", "Xem phiếu nhập"),
        ("phieu_nhap.tao", "Lập phiếu nhập (nhập tay hoặc Excel)"),
        ("phieu_tra.xem", "Xem phiếu trả nhà cung cấp"),
        ("phieu_tra.tao", "Lập phiếu trả nhà cung cấp"),
        ("dieu_chuyen.xem", "Xem phiếu điều chuyển"),
        ("dieu_chuyen.tao", "Lập và xác nhận điều chuyển"),
        ("kiem_ke.xem", "Xem phiếu kiểm kê"),
        ("kiem_ke.tao", "Lập phiếu kiểm kê"),
        ("xuat_huy.xem", "Xem phiếu xuất hủy"),
        ("xuat_huy.tao", "Lập phiếu xuất hủy"),
    ),
    *_q(
        "Bán hàng",
        ("phieu_ban.xem", "Xem phiếu bán tại quầy"),
        ("phieu_ban.tao", "Bán hàng tại quầy"),
        (
            "thuoc_ke_don.ban",
            "Bán thuốc kê đơn tại quầy",
            "Giao cho dược sĩ: kiểm tra đơn thuốc, ghi bác sĩ, người bệnh, ngày kê đơn.",
        ),
        ("don_hang.xem", "Xem đơn đặt giữ"),
        ("don_hang.xu_ly", "Giao đơn đặt giữ tại quầy, hủy đơn"),
        ("hoa_don_cong_ty.xem", "Xem yêu cầu hóa đơn công ty"),
        ("hoa_don_cong_ty.xu_ly", "Xử lý yêu cầu hóa đơn công ty"),
        ("tro_chuyen.dung", "Trò chuyện với khách"),
    ),
    *_q(
        "Phân tích",
        ("bao_cao.xem", "Xem và xuất báo cáo doanh thu"),
        ("du_bao.xem", "Xem kết quả dự báo"),
        ("du_bao.chay", "Chạy kịch bản dự báo"),
        ("ban_do_nhiet.xem", "Xem bản đồ nhiệt tồn kho"),
    ),
    *_q(
        "Website",
        ("banner.sua", "Quản lý banner trang chủ"),
        ("trang.sua", "Quản lý trang chính sách"),
        ("tin_tuc.sua", "Quản lý tin tức"),
        ("thong_tin.sua", "Sửa thông tin cửa hàng"),
        ("email.xem", "Xem nhật ký email hệ thống"),
    ),
    *_q(
        "Hệ thống",
        ("tai_khoan.xem", "Xem tài khoản", "", True),
        ("tai_khoan.sua", "Tạo, sửa, khóa tài khoản", "", True),
        ("phan_quyen.quan_ly", "Quản lý nhóm quyền và quyền riêng", "", True),
        ("mo_phong.tao", "Tạo dữ liệu mô phỏng", "", True),
    ),
]
THEO_MA = {quyen.ma: quyen for quyen in DANH_SACH_QUYEN}
MA_QUYEN = frozenset(THEO_MA)
QUYEN_GIAO_DUOC = frozenset(q.ma for q in DANH_SACH_QUYEN if not q.chi_quan_tri)

_XEM_CHUNG = {
    "chi_nhanh.xem",
    "thuoc.xem",
    "danh_muc_san_pham.xem",
    "khuyen_mai.xem",
    "nhom_atc.xem",
    "don_vi_tinh.xem",
    "quy_doi_bao_goi.xem",
    "nha_cung_cap.xem",
    "nhan_vien.xem",
    "ton_kho.xem",
    "phieu_nhap.xem",
    "phieu_nhap.tao",
    "phieu_ban.xem",
    "phieu_ban.tao",
    "don_hang.xem",
    "don_hang.xu_ly",
    "hoa_don_cong_ty.xem",
    "hoa_don_cong_ty.xu_ly",
    "tro_chuyen.dung",
}
_THEM_CHO_QUAN_LY = {
    "lo_thuoc.xem",
    "phieu_tra.xem",
    "phieu_tra.tao",
    "dieu_chuyen.xem",
    "dieu_chuyen.tao",
    "kiem_ke.xem",
    "kiem_ke.tao",
    "xuat_huy.xem",
    "xuat_huy.tao",
    "bao_cao.xem",
    # Quản lý chi nhánh (dược sĩ phụ trách chuyên môn) mặc định bán được thuốc kê đơn;
    # nhân viên là dược sĩ được cấp riêng bằng quyền riêng hoặc nhóm quyền.
    "thuoc_ke_don.ban",
}
MAC_DINH = {
    NHAN_VIEN: frozenset(_XEM_CHUNG),
    QUAN_LY: frozenset(_XEM_CHUNG | _THEM_CHO_QUAN_LY),
}
TEN_NHOM_MAC_DINH = {
    QUAN_LY: ("QUAN-LY-MAC-DINH", "Quản lý chi nhánh (mặc định)"),
    NHAN_VIEN: ("NHAN-VIEN-MAC-DINH", "Nhân viên (mặc định)"),
}


def nhom_theo_module():
    """Quyền giao được, gom theo nhóm hiển thị trên form phân quyền."""
    ket_qua = {}
    for quyen in DANH_SACH_QUYEN:
        if not quyen.chi_quan_tri:
            ket_qua.setdefault(quyen.nhom, []).append(quyen)
    return ket_qua
