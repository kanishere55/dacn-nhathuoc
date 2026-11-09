"""Nội dung hiển thị của chứng từ kho: một nguồn cho trang chi tiết và bản PDF."""

from decimal import Decimal
from io import BytesIO

from django.utils import timezone

from ung_dung.chung.phong_pdf import dang_ky_phong_pdf

from .models import (
    ChiTietPhieuDieuChuyen,
    ChiTietPhieuKiemKe,
    ChiTietPhieuNhap,
    ChiTietPhieuTraNhaCungCap,
    ChiTietPhieuXuatHuy,
    PhieuDieuChuyen,
    PhieuKiemKe,
    PhieuNhap,
    PhieuTraNhaCungCap,
    PhieuXuatHuy,
)


def _tien(so):
    return f"{Decimal(so):,.0f} đ".replace(",", ".")


def _so(so):
    return f"{so:,}".replace(",", ".")


def _ten_nguoi(tai_khoan):
    return tai_khoan.ho_ten or tai_khoan.ten_dang_nhap


def _cot_lo(dong):
    lo = dong.lo_thuoc
    return [
        lo.thuoc.ten_thuoc,
        lo.ma_lo_thuoc,
        f"{lo.ngay_het_han:%d/%m/%Y}",
    ]


def _cac_dong(model, **loc):
    return (
        model.objects.filter(**loc)
        .select_related("lo_thuoc__thuoc__don_vi_tinh")
        .order_by("lo_thuoc__thuoc__ten_thuoc", "lo_thuoc__ngay_het_han", "pk")
    )


COT_LO = [("Thuốc", False), ("Lô", False), ("Hạn dùng", False)]


def du_lieu_chung_tu(phieu):
    """Trả tiêu đề, thông tin đầu phiếu, bảng dòng và tổng của một chứng từ kho."""
    tong = []
    if isinstance(phieu, PhieuNhap):
        tieu_de, ten = "Phiếu nhập kho", "phieu_nhap"
        thong_tin = [
            ("Chi nhánh nhận", phieu.chi_nhanh.ten_chi_nhanh),
            ("Nhà cung cấp", phieu.nha_cung_cap.ten_nha_cung_cap),
        ]
        cot = [*COT_LO, ("Số lượng", True), ("Đơn giá", True), ("Thành tiền", True)]
        hang, tong_tien = [], Decimal(0)
        for dong in _cac_dong(ChiTietPhieuNhap, phieu_nhap=phieu):
            thanh_tien = dong.don_gia * dong.so_luong
            tong_tien += thanh_tien
            hang.append(
                [
                    *_cot_lo(dong),
                    f"{_so(dong.so_luong)} {dong.lo_thuoc.thuoc.don_vi_tinh.ten_don_vi_tinh}",
                    _tien(dong.don_gia),
                    _tien(thanh_tien),
                ]
            )
        tong = [("Tổng tiền nhập", _tien(tong_tien))]
        ben_ky = "Người giao hàng"
    elif isinstance(phieu, PhieuTraNhaCungCap):
        goc = phieu.phieu_nhap
        tieu_de, ten = "Phiếu trả nhà cung cấp", "phieu_tra"
        thong_tin = [
            ("Chi nhánh trả", goc.chi_nhanh.ten_chi_nhanh),
            ("Nhà cung cấp", goc.nha_cung_cap.ten_nha_cung_cap),
            ("Phiếu nhập gốc", goc.ma_phieu_nhap),
        ]
        cot = [*COT_LO, ("Số lượng", True)]
        hang = [
            [*_cot_lo(d), f"{_so(d.so_luong)} {d.lo_thuoc.thuoc.don_vi_tinh.ten_don_vi_tinh}"]
            for d in _cac_dong(ChiTietPhieuTraNhaCungCap, phieu_tra_nha_cung_cap=phieu)
        ]
        ben_ky = "Đại diện nhà cung cấp"
    elif isinstance(phieu, PhieuDieuChuyen):
        tieu_de, ten = "Phiếu điều chuyển kho", "phieu_dieu_chuyen"
        thong_tin = [
            ("Chi nhánh xuất", phieu.chi_nhanh_nguon.ten_chi_nhanh),
            ("Chi nhánh nhận", phieu.chi_nhanh_dich.ten_chi_nhanh),
        ]
        cot = [*COT_LO, ("Số lượng", True)]
        hang = [
            [*_cot_lo(d), f"{_so(d.so_luong)} {d.lo_thuoc.thuoc.don_vi_tinh.ten_don_vi_tinh}"]
            for d in _cac_dong(ChiTietPhieuDieuChuyen, phieu_dieu_chuyen=phieu)
        ]
        ben_ky = "Người nhận hàng"
    elif isinstance(phieu, PhieuKiemKe):
        tieu_de, ten = "Biên bản kiểm kê", "phieu_kiem_ke"
        thong_tin = [("Chi nhánh", phieu.chi_nhanh.ten_chi_nhanh)]
        cot = [*COT_LO, ("Sổ sách", True), ("Thực tế", True), ("Chênh lệch", True)]
        hang = []
        for d in _cac_dong(ChiTietPhieuKiemKe, phieu_kiem_ke=phieu):
            lech = d.so_luong_thuc_te - d.so_luong_so_sach
            hang.append(
                [
                    *_cot_lo(d),
                    _so(d.so_luong_so_sach),
                    _so(d.so_luong_thuc_te),
                    ("+" if lech > 0 else "") + _so(lech),
                ]
            )
        ben_ky = "Người chứng kiến"
    elif isinstance(phieu, PhieuXuatHuy):
        tieu_de, ten = "Phiếu xuất hủy", "phieu_xuat_huy"
        thong_tin = [
            ("Chi nhánh", phieu.chi_nhanh.ten_chi_nhanh),
            ("Lý do", phieu.get_loai_xuat_huy_display()),
        ]
        cot = [*COT_LO, ("Số lượng", True)]
        hang = [
            [*_cot_lo(d), f"{_so(d.so_luong)} {d.lo_thuoc.thuoc.don_vi_tinh.ten_don_vi_tinh}"]
            for d in _cac_dong(ChiTietPhieuXuatHuy, phieu_xuat_huy=phieu)
        ]
        ben_ky = "Người chứng kiến"
    else:
        raise TypeError(f"Không phải chứng từ kho: {type(phieu).__name__}")
    thong_tin += [
        ("Người lập", _ten_nguoi(phieu.nguoi_lap)),
        ("Thời điểm", f"{timezone.localtime(phieu.thoi_diem_tao):%H:%M %d/%m/%Y}"),
    ]
    return {
        "phieu": phieu,
        "tieu_de": tieu_de,
        "ma": str(phieu),
        "ten": ten,
        "thong_tin": thong_tin,
        "ghi_chu": phieu.ghi_chu,
        "cot": cot,
        "hang": hang,
        "tong": tong,
        "ben_ky": ben_ky,
    }


def ten_tep_pdf(du_lieu):
    return f"{du_lieu['ten'].replace('_', '-')}-{du_lieu['ma']}.pdf"


def ve_pdf(du_lieu, ten_thuong_hieu):
    """Trả bytes PDF khổ A4 của chứng từ, có ô ký ở cuối trang."""
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    dang_ky_phong_pdf()
    xanh = colors.HexColor("#116b54")
    xam = colors.HexColor("#5b6d64")
    vien = colors.HexColor("#d9e3dc")
    chu = ParagraphStyle("chu", fontName="BeVietnamPro", fontSize=9.5, leading=13.5)
    nho = ParagraphStyle("nho", parent=chu, fontSize=8.5, leading=12, textColor=xam)
    dam = ParagraphStyle("dam", parent=chu, fontName="BeVietnamPro-Dam")
    phai = ParagraphStyle("phai", parent=chu, alignment=TA_RIGHT)
    phai_dam = ParagraphStyle("phai_dam", parent=dam, alignment=TA_RIGHT)
    giua = ParagraphStyle("giua", parent=dam, alignment=TA_CENTER)
    giua_nho = ParagraphStyle("giua_nho", parent=nho, alignment=TA_CENTER)
    tieu_de = ParagraphStyle(
        "tieu_de", parent=dam, fontSize=16, leading=20, textColor=xanh, alignment=TA_RIGHT
    )

    def p(van_ban, kieu=chu):
        return Paragraph(escape(str(van_ban)).replace("\n", "<br/>"), kieu)

    dem = BytesIO()
    tai_lieu = SimpleDocTemplate(
        dem,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"{du_lieu['tieu_de']} {du_lieu['ma']}",
        author=ten_thuong_hieu,
    )
    rong = A4[0] - 32 * mm
    dau = Table(
        [
            [
                p(ten_thuong_hieu, ParagraphStyle("hieu", parent=dam, fontSize=13, textColor=xanh)),
                [p(du_lieu["tieu_de"].upper(), tieu_de), p(f"Số: {du_lieu['ma']}", phai)],
            ]
        ],
        colWidths=[rong * 0.5, rong * 0.5],
    )
    dau.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    thong_tin = Table(
        [[p(nhan, nho), p(gia_tri)] for nhan, gia_tri in du_lieu["thong_tin"]],
        colWidths=[rong * 0.22, rong * 0.78],
    )
    thong_tin.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ]
        )
    )
    # Độ rộng theo điểm in: STT, lô, hạn dùng và cột số cố định để không ngắt dòng;
    # cột tên thuốc nhận phần còn lại.
    so_cot_so = len(du_lieu["cot"]) - 3
    rong_so = 70 if so_cot_so == 1 else 64
    rong_cot = [26, None, 60, 72, *([rong_so] * so_cot_so)]
    rong_cot[1] = rong - sum(w for w in rong_cot if w)
    hang = [[p("STT", dam), *(p(nhan, phai_dam if so else dam) for nhan, so in du_lieu["cot"])]]
    for stt, dong in enumerate(du_lieu["hang"], start=1):
        hang.append(
            [
                p(stt),
                *(
                    p(o, phai if so else chu)
                    for o, (_, so) in zip(dong, du_lieu["cot"], strict=True)
                ),
            ]
        )
    bang = Table(hang, colWidths=rong_cot, repeatRows=1)
    bang.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, xanh),
                ("LINEBELOW", (0, 1), (-1, -1), 0.4, vien),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    noi_dung = [dau, Spacer(1, 6 * mm), thong_tin, Spacer(1, 5 * mm), bang]
    for nhan, gia_tri in du_lieu["tong"]:
        noi_dung += [Spacer(1, 3 * mm), p(f"{nhan}: {gia_tri}", phai_dam)]
    if du_lieu["ghi_chu"]:
        noi_dung += [Spacer(1, 4 * mm), p("Ghi chú", nho), p(du_lieu["ghi_chu"])]
    o_ky = Table(
        [
            [p("Người lập phiếu", giua), p(du_lieu["ben_ky"], giua)],
            [p("(Ký, ghi rõ họ tên)", giua_nho), p("(Ký, ghi rõ họ tên)", giua_nho)],
            [Spacer(1, 18 * mm), Spacer(1, 18 * mm)],
            [p(_ten_nguoi(du_lieu["phieu"].nguoi_lap), giua), p("")],
        ],
        colWidths=[rong * 0.5, rong * 0.5],
    )
    noi_dung += [Spacer(1, 10 * mm), o_ky]
    tai_lieu.build(noi_dung)
    return dem.getvalue()
