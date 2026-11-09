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
            ("Doanh thu bán hàng", bao_cao["doanh_thu_gop"]),
            ("Hoàn tiền cho khách", bao_cao["tien_hoan_khach"]),
            ("Doanh thu thuần", bao_cao["doanh_thu_thuan"]),
            ("Phiếu đã hoàn kho (không tính doanh thu)", bao_cao["tien_hoan_kho"]),
        ],
        cot_tien=(1,),
    )
    _bang(
        tong,
        "Thu theo phương thức",
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
            ("Đơn hàng", bao_cao["so_don_giu"]),
            ("Trả nhà cung cấp", bao_cao["so_phieu_tra"]),
            ("Điều chuyển", bao_cao["so_phieu_chuyen"]),
            ("Kiểm kê", bao_cao["so_phieu_kiem_ke"]),
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
        "Biến động trong kỳ theo đơn vị cơ sở",
        ["Đơn vị", "Nhập", "Bán", "Trả NCC", "Chuyển đi", "Chuyển đến", "Điều chỉnh", "Khả dụng"],
        [
            (
                don_vi,
                *(
                    d.get(k, 0) or 0
                    for k in (
                        "nhap",
                        "ban",
                        "tra",
                        "chuyen_di",
                        "chuyen_den",
                        "dieu_chinh",
                        "kha_dung",
                    )
                ),
            )
            for don_vi, d in bao_cao["cac_luong"]
        ],
    )
    for trang in so.worksheets:
        for chi_so, cot in enumerate(trang.columns, start=1):
            rong = max((len(str(o.value)) for o in cot if o.value is not None), default=8)
            trang.column_dimensions[get_column_letter(chi_so)].width = min(max(rong + 2, 10), 48)
    dem = BytesIO()
    so.save(dem)
    return dem.getvalue()
