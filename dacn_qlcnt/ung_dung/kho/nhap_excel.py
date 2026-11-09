"""Đọc tệp Excel thành các dòng phiếu nhập để xem trước, và tạo tệp mẫu.

Tệp chỉ được đọc trong bộ nhớ, không lưu xuống đĩa. Việc ghi kho vẫn đi qua
`nhap_hang()` sau khi người dùng xem lại và bấm xác nhận.
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils.exceptions import InvalidFileException

from ung_dung.chung.ten_csdl import MA_NGHIEP_VU
from ung_dung.danh_muc.models import QuyDoiBaoGoi, Thuoc

SO_DONG_TOI_DA = 50
COT = (
    ("ma_thuoc", "Mã thuốc"),
    ("ma_lo_thuoc", "Mã lô"),
    ("ngay_het_han", "Ngày hết hạn"),
    ("so_luong", "Số lượng"),
    ("bao_goi", "Bao gói"),
    ("don_gia", "Giá nhập / đơn vị cơ sở"),
)
COT_BAT_BUOC = {"ma_thuoc", "ma_lo_thuoc", "ngay_het_han", "so_luong", "don_gia"}


class LoiTepExcel(Exception):
    pass


def _chuan_hoa_tieu_de(gia_tri):
    return re.sub(r"\s+", " ", str(gia_tri or "")).strip().lower()


def _doc_ngay(gia_tri):
    if isinstance(gia_tri, datetime):
        return gia_tri.date()
    if isinstance(gia_tri, date):
        return gia_tri
    van_ban = str(gia_tri or "").strip()
    for mau in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(van_ban, mau).date()
        except ValueError:
            continue
    raise ValueError("ngày hết hạn cần dạng ngày/tháng/năm")


def _doc_so_nguyen(gia_tri, ten, *, duong):
    if isinstance(gia_tri, bool):
        raise ValueError(f"{ten} phải là số")
    # Ô số giữ nguyên giá trị; ô chữ kiểu "12.000" bỏ dấu phân cách hàng nghìn.
    van_ban = str(gia_tri) if isinstance(gia_tri, int | float | Decimal) else str(gia_tri or "")
    if not isinstance(gia_tri, int | float | Decimal):
        van_ban = van_ban.strip().replace(".", "").replace(",", "").replace(" ", "")
    try:
        so = Decimal(van_ban)
    except InvalidOperation:
        raise ValueError(f"{ten} phải là số") from None
    if not so.is_finite() or so != so.to_integral_value():
        raise ValueError(f"{ten} phải là số nguyên")
    if so < (1 if duong else 0) or so > 2147483647:
        raise ValueError(f"{ten} nằm ngoài khoảng cho phép")
    return int(so)


def doc_tep_nhap(tep):
    """Trả (các dòng ban đầu cho formset, các lỗi theo số dòng Excel)."""
    try:
        so = load_workbook(BytesIO(tep.read()), read_only=True, data_only=True)
    except (InvalidFileException, BadZipFile, OSError, KeyError, ValueError):
        raise LoiTepExcel("Không đọc được tệp. Hãy dùng tệp .xlsx tạo từ mẫu.") from None
    try:
        cac_hang = so.worksheets[0].iter_rows(values_only=True)
        tieu_de = [_chuan_hoa_tieu_de(o) for o in next(cac_hang, ())]
        vi_tri = {}
        for ma, nhan in COT:
            if _chuan_hoa_tieu_de(nhan) in tieu_de:
                vi_tri[ma] = tieu_de.index(_chuan_hoa_tieu_de(nhan))
        thieu = [nhan for ma, nhan in COT if ma in COT_BAT_BUOC and ma not in vi_tri]
        if thieu:
            raise LoiTepExcel("Tệp thiếu cột: " + ", ".join(thieu) + ".")
        cac_thuoc = {t.ma_thuoc: t for t in Thuoc.objects.filter(dang_hoat_dong=True)}
        cac_dong, cac_loi = [], []
        for so_dong, hang in enumerate(cac_hang, start=2):
            o = {ma: hang[i] if i < len(hang) else None for ma, i in vi_tri.items()}
            if all(gia_tri in (None, "") for gia_tri in o.values()):
                continue
            if len(cac_dong) + len(cac_loi) >= SO_DONG_TOI_DA:
                raise LoiTepExcel(f"Một phiếu nhập tối đa {SO_DONG_TOI_DA} dòng.")
            try:
                cac_dong.append(_doc_dong(o, cac_thuoc))
            except ValueError as loi:
                cac_loi.append(f"Dòng {so_dong}: {loi}.")
    finally:
        so.close()
    if not cac_dong and not cac_loi:
        raise LoiTepExcel("Tệp chưa có dòng hàng nào dưới tiêu đề.")
    return cac_dong, cac_loi


def _doc_dong(o, cac_thuoc):
    ma_thuoc = str(o["ma_thuoc"] or "").strip().upper()
    thuoc = cac_thuoc.get(ma_thuoc)
    if not thuoc:
        raise ValueError(f"không có thuốc đang kinh doanh mã {ma_thuoc or '(trống)'}")
    ma_lo = str(o["ma_lo_thuoc"] or "").strip()
    if not re.fullmatch(MA_NGHIEP_VU, ma_lo):
        raise ValueError("mã lô gồm tối đa 32 chữ hoa, số, gạch ngang hoặc gạch dưới")
    ngay_het_han = _doc_ngay(o["ngay_het_han"])
    so_luong = _doc_so_nguyen(o["so_luong"], "số lượng", duong=True)
    don_gia = _doc_so_nguyen(o["don_gia"], "giá nhập", duong=False)
    quy_doi = None
    ten_bao_goi = str(o.get("bao_goi") or "").strip()
    if ten_bao_goi:
        quy_doi = QuyDoiBaoGoi.objects.filter(
            thuoc=thuoc, ten_quy_doi_bao_goi__iexact=ten_bao_goi
        ).first()
        if not quy_doi:
            raise ValueError(f"thuốc {ma_thuoc} chưa khai báo bao gói “{ten_bao_goi}”")
    return {
        "thuoc": thuoc.pk,
        "ma_lo_thuoc": ma_lo,
        # Chuỗi ISO để ô <input type="date"> hiển thị đúng, không theo định dạng địa phương.
        "ngay_het_han": ngay_het_han.isoformat(),
        "so_luong": so_luong,
        "quy_doi_bao_goi": quy_doi.pk if quy_doi else None,
        "don_gia": don_gia,
    }


def tao_tep_mau():
    """Trả bytes tệp mẫu: trang nhập liệu và trang tra cứu mã thuốc, bao gói."""
    so = Workbook()
    nhap = so.active
    nhap.title = "Phiếu nhập"
    dam = Font(bold=True, color="FFFFFF")
    nen = PatternFill("solid", fgColor="116B54")
    nhap.append([nhan for _, nhan in COT])
    for o in nhap[1]:
        o.font, o.fill = dam, nen
    for cot, rong in zip("ABCDEF", (14, 16, 15, 11, 12, 24), strict=True):
        nhap.column_dimensions[cot].width = rong
    tra_cuu = so.create_sheet("Mã thuốc")
    tra_cuu.append(["Mã thuốc", "Tên thuốc", "Đơn vị cơ sở", "Bao gói (hệ số)"])
    for o in tra_cuu[1]:
        o.font, o.fill = dam, nen
    for thuoc in (
        Thuoc.objects.filter(dang_hoat_dong=True)
        .select_related("don_vi_tinh")
        .prefetch_related("quydoibaogoi_set")
        .order_by("ma_thuoc")
    ):
        bao_goi = ", ".join(
            f"{q.ten_quy_doi_bao_goi} ({q.he_so})" for q in thuoc.quydoibaogoi_set.all()
        )
        tra_cuu.append(
            [thuoc.ma_thuoc, thuoc.ten_thuoc, thuoc.don_vi_tinh.ten_don_vi_tinh, bao_goi]
        )
    for cot, rong in zip("ABCD", (14, 42, 14, 30), strict=True):
        tra_cuu.column_dimensions[cot].width = rong
    dem = BytesIO()
    so.save(dem)
    return dem.getvalue()
