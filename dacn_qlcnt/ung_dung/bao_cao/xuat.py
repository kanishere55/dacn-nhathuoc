"""Xuất báo cáo vận hành ra Excel (openpyxl), cùng số liệu với trang báo cáo."""

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

XANH = PatternFill("solid", fgColor="116B54")
DINH_DANG_TIEN = '#,##0" đ"'


def _bang(trang, tieu_de, cac_cot, cac_dong, cot_tien=()):
    trang.append([tieu_de])
    trang.cell(trang.max_row, 1).font = Font(bold=True, size=13)
    trang.append(cac_cot)
    for o in trang[trang.max_row]:
        o.font = Font(bold=True, color="FFFFFF")
        o.fill = XANH
        o.alignment = Alignment(vertical="center")
    for dong in cac_dong:
        trang.append(list(dong))
        for o in trang[trang.max_row]:
            # openpyxl coi chuỗi bắt đầu bằng "=" là công thức; dữ liệu người dùng nhập
            # (tên thuốc...) luôn ghi dạng văn bản để không chạy công thức khi mở file.
            if isinstance(o.value, str):
                o.data_type = "s"
        for chi_so in cot_tien:
            trang.cell(trang.max_row, chi_so + 1).number_format = DINH_DANG_TIEN
    trang.append([])


def xuat_excel(bao_cao, *, tu_ngay, den_ngay, ten_chi_nhanh):
    so = Workbook()
    tong = so.active
    tong.title = "Tổng hợp"
    tong.append([f"Báo cáo vận hành {ten_chi_nhanh}"])
    tong["A1"].font = Font(bold=True, size=15, color="116B54")
    tong.append([f"Từ {tu_ngay:%d/%m/%Y} đến {den_ngay:%d/%m/%Y}"])
    tong.append([])
    _bang(
        tong,
        "Doanh thu",
        ["Chỉ tiêu", "Số tiền"],
        [
            ("Doanh thu bán hàng (sau ưu đãi thành viên)", bao_cao["doanh_thu"]),
            ("Trung bình mỗi phiếu bán", bao_cao["trung_binh_phieu"]),
        ],
        cot_tien=(1,),
    )
    _bang(
        tong,
        "Đã thu tại quầy theo phương thức",
        ["Phương thức", "Số tiền"],
        bao_cao["theo_phuong_thuc"],
        cot_tien=(1,),
    )
    _bang(
        tong,
        "Chứng từ trong kỳ",
        ["Loại", "Số lượng"],
        [
            ("Phiếu nhập", bao_cao["so_phieu_nhap"]),
            ("Phiếu bán", bao_cao["so_phieu_ban"]),
            ("Đơn đặt giữ mới (kể cả đã hủy, hết hạn)", bao_cao["so_don_giu"]),
            ("Đơn đặt giữ khách đã nhận", bao_cao["so_don_da_nhan"]),
            ("Trả nhà cung cấp", bao_cao["so_phieu_tra"]),
            ("Điều chuyển", bao_cao["so_phieu_chuyen"]),
            ("Kiểm kê", bao_cao["so_phieu_kiem_ke"]),
            ("Xuất hủy", bao_cao["so_phieu_xuat_huy"]),
        ],
    )
    ban_chay = so.create_sheet("Thuốc bán chạy")
    _bang(
        ban_chay,
        "Thuốc bán chạy theo doanh thu",
        ["Mã thuốc", "Tên thuốc", "Đơn vị", "Số lượng", "Doanh thu"],
        [
            (
                d["thuoc__ma_thuoc"],
                d["thuoc__ten_thuoc"],
                d["thuoc__don_vi_tinh__ten_don_vi_tinh"],
                d["tong_so_luong"],
                d["doanh_thu"],
            )
            for d in bao_cao["ban_chay"]
        ],
        cot_tien=(4,),
    )
    kho = so.create_sheet("Biến động kho")
    _bang(
        kho,
        "Nhập – xuất – tồn trong kỳ theo đơn vị cơ sở",
        ["Đơn vị", *(nhan for _, nhan in bao_cao["cot_bien_dong"])],
        [(don_vi, *cac_so) for don_vi, cac_so in bao_cao["bang_bien_dong"]],
    )
    kho.append(
        [
            "Tồn đầu kỳ + nhập, chuyển đến, hoàn kho, nhập lại, điều chỉnh − bán, chuyển đi, "
            "trả NCC, xuất hủy = tồn cuối kỳ. Khả dụng hiện tại là số tại lúc xuất tệp."
        ]
    )
    for trang in so.worksheets:
        for chi_so, cot in enumerate(trang.columns, start=1):
            rong = max((len(str(o.value)) for o in cot if o.value is not None), default=8)
            trang.column_dimensions[get_column_letter(chi_so)].width = min(max(rong + 2, 10), 48)
    dem = BytesIO()
    so.save(dem)
    return dem.getvalue()
