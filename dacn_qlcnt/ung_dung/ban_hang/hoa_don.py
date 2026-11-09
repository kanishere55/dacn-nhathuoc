"""Hóa đơn bán lẻ của phiếu bán: dữ liệu chung cho trang in, PDF và email.

Đây là chứng từ bán hàng nội bộ của nhà thuốc, không thay thế hóa đơn điện tử theo
Nghị định 123/2020/NĐ-CP (sửa đổi bởi Nghị định 70/2025/NĐ-CP).
"""

from collections import OrderedDict
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone

from ung_dung.thanh_toan.models import GiaoDichThanhToan

from .models import ChiTietPhieuBan, PhanBoPhieuBan, PhieuBan, PhieuHoanKho

CHU_SO = ("không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín")
TEN_NHOM = ("", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ")
GHI_CHU_PHAP_LY = (
    "Chứng từ bán hàng nội bộ của nhà thuốc, không thay thế hóa đơn điện tử. "
    "Cần hóa đơn điện tử, vui lòng liên hệ nhà thuốc."
)


def _doc_ba_chu_so(so, day_du):
    """Đọc 0-999; `day_du` khi nhóm đứng sau nhóm khác (đọc cả "không trăm", "linh")."""
    tram, chuc, don_vi = so // 100, so // 10 % 10, so % 10
    cac_tu = []
    if day_du or tram:
        cac_tu += [CHU_SO[tram], "trăm"]
    if chuc == 0:
        if don_vi and cac_tu:
            cac_tu.append("linh")
    elif chuc == 1:
        cac_tu.append("mười")
    else:
        cac_tu += [CHU_SO[chuc], "mươi"]
    if don_vi:
        if don_vi == 1 and chuc > 1:
            cac_tu.append("mốt")
        elif don_vi == 4 and chuc > 1:
            cac_tu.append("tư")
        elif don_vi == 5 and chuc > 0:
            cac_tu.append("lăm")
        else:
            cac_tu.append(CHU_SO[don_vi])
    return " ".join(cac_tu)


def doc_so(so):
    """Đọc số nguyên không âm bằng chữ tiếng Việt, ví dụ 19500 -> mười chín nghìn năm trăm."""
    so = int(so)
    if so < 0 or so >= 1000 ** len(TEN_NHOM):
        raise ValueError("Số nằm ngoài phạm vi đọc.")
    if so == 0:
        return CHU_SO[0]
    cac_nhom = []
    while so:
        so, du = divmod(so, 1000)
        cac_nhom.append(du)
    cac_phan = []
    for vi_tri in range(len(cac_nhom) - 1, -1, -1):
        nhom = cac_nhom[vi_tri]
        if nhom:
            chu = _doc_ba_chu_so(nhom, day_du=vi_tri < len(cac_nhom) - 1)
            cac_phan.append(f"{chu} {TEN_NHOM[vi_tri]}".strip())
    return " ".join(cac_phan)


def doc_tien(so_tien):
    chu = doc_so(Decimal(so_tien).quantize(Decimal(1)))
    return f"{chu[0].upper()}{chu[1:]} đồng"


def du_lieu_hoa_don(phieu):
    phieu = PhieuBan.objects.select_related("chi_nhanh", "nguoi_lap", "don_hang__khach_hang").get(
        pk=phieu.pk
    )
    cac_chi_tiet = (
        ChiTietPhieuBan.objects.filter(phieu_ban=phieu)
        .select_related("thuoc__don_vi_tinh")
        .prefetch_related(
            Prefetch(
                "phanbophieuban_set",
                queryset=PhanBoPhieuBan.objects.select_related("ton_kho__lo_thuoc").order_by(
                    "ton_kho__lo_thuoc__ngay_het_han", "pk"
                ),
            )
        )
        .order_by("pk")
    )
    cac_dong = []
    tien_hang = Decimal(0)
    for so_thu_tu, chi_tiet in enumerate(cac_chi_tiet, start=1):
        cac_lo = OrderedDict()
        for phan_bo in chi_tiet.phanbophieuban_set.all():
            lo = phan_bo.ton_kho.lo_thuoc
            cac_lo.setdefault((lo.ma_lo_thuoc, lo.ngay_het_han), 0)
            cac_lo[(lo.ma_lo_thuoc, lo.ngay_het_han)] += phan_bo.so_luong
        thanh_tien = chi_tiet.don_gia * chi_tiet.so_luong
        tien_hang += thanh_tien
        cac_dong.append(
            {
                "stt": so_thu_tu,
                "ten": chi_tiet.ten_thuoc_luc_ban,
                "ma": chi_tiet.ma_thuoc_luc_ban,
                "don_vi": chi_tiet.thuoc.don_vi_tinh.ten_don_vi_tinh,
                "so_luong": chi_tiet.so_luong,
                "don_gia": chi_tiet.don_gia,
                "thanh_tien": thanh_tien,
                "ke_don": chi_tiet.thuoc.la_thuoc_ke_don,
                "cac_lo": [
                    {"ma": ma, "han_dung": han, "so_luong": luong}
                    for (ma, han), luong in cac_lo.items()
                ],
            }
        )
    don = phieu.don_hang
    giao_dich = GiaoDichThanhToan.objects.filter(trang_thai="thanh_cong")
    giao_dich = giao_dich.filter(don_hang=don) if don else giao_dich.filter(phieu_ban=phieu)
    if don:
        khach = {
            "ten": don.ten_nguoi_nhan or don.khach_hang.ho_ten or don.khach_hang.ten_dang_nhap,
            "so_dien_thoai": don.so_dien_thoai_nhan or don.khach_hang.so_dien_thoai,
            "dia_chi": don.dia_chi_giao,
        }
        tong = {
            "tien_hang": don.tien_hang,
            "giam_gia": don.giam_gia_thanh_vien,
            "phi_giao": don.phi_giao_hang,
            "khoang_cach_met": don.khoang_cach_met,
            "tong": don.tong_thanh_toan,
        }
    else:
        khach = {"ten": "Khách mua tại quầy", "so_dien_thoai": "", "dia_chi": ""}
        tong = {
            "tien_hang": tien_hang,
            "giam_gia": 0,
            "phi_giao": 0,
            "khoang_cach_met": None,
            "tong": tien_hang,
        }
    cac_khoan = list(giao_dich.order_by("thoi_diem_hoan_tat", "pk"))
    da_thu = sum((k.so_tien for k in cac_khoan if k.loai_giao_dich == "thu"), Decimal(0))
    da_hoan = sum((k.so_tien for k in cac_khoan if k.loai_giao_dich == "hoan"), Decimal(0))
    return {
        "phieu": phieu,
        "don": don,
        "chi_nhanh": phieu.chi_nhanh,
        "ten_thuong_hieu": settings.TEN_THUONG_HIEU,
        "url_website": settings.URL_WEBSITE,
        "thoi_diem": timezone.localtime(phieu.thoi_diem_tao),
        "nguoi_ban": phieu.nguoi_lap.ho_ten or phieu.nguoi_lap.ten_dang_nhap,
        "khach": khach,
        "cac_dong": cac_dong,
        "tong": tong,
        "bang_chu": doc_tien(tong["tong"]),
        "cac_khoan": cac_khoan,
        "con_phai_thu": Decimal(0) if da_hoan else max(tong["tong"] - da_thu, Decimal(0)),
        "da_hoan": da_hoan,
        "da_hoan_kho": PhieuHoanKho.objects.filter(phieu_ban=phieu).exists(),
        "ghi_chu_phap_ly": GHI_CHU_PHAP_LY,
    }


def ten_tep_pdf(phieu):
    return f"hoa-don-{phieu.ma_phieu_ban}.pdf"


# ---------------------------------------------------------------- PDF (ReportLab)

THU_MUC_PHONG = Path(settings.BASE_DIR) / "static" / "vendor" / "be_vietnam_pro"
_DA_DANG_KY_PHONG = False


def _dang_ky_phong():
    global _DA_DANG_KY_PHONG
    if _DA_DANG_KY_PHONG:
        return
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for ten, tep in (
        ("BeVietnamPro", "BeVietnamPro-Regular.ttf"),
        ("BeVietnamPro-Dam", "BeVietnamPro-Bold.ttf"),
        ("BeVietnamPro-Vua", "BeVietnamPro-SemiBold.ttf"),
    ):
        pdfmetrics.registerFont(TTFont(ten, str(THU_MUC_PHONG / tep)))
    addMapping("BeVietnamPro", 0, 0, "BeVietnamPro")
    addMapping("BeVietnamPro", 1, 0, "BeVietnamPro-Dam")
    _DA_DANG_KY_PHONG = True


def _tien(so):
    return f"{Decimal(so):,.0f} đ".replace(",", ".")


def ve_pdf(du_lieu):
    """Trả bytes PDF khổ A4 của hóa đơn."""
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    _dang_ky_phong()
    xanh = colors.HexColor("#116b54")
    xam = colors.HexColor("#5b6d64")
    vien = colors.HexColor("#d9e3dc")
    chu = ParagraphStyle("chu", fontName="BeVietnamPro", fontSize=9.5, leading=13.5)
    nho = ParagraphStyle("nho", parent=chu, fontSize=8, leading=11, textColor=xam)
    dam = ParagraphStyle("dam", parent=chu, fontName="BeVietnamPro-Dam")
    phai = ParagraphStyle("phai", parent=chu, alignment=TA_RIGHT)
    phai_dam = ParagraphStyle("phai_dam", parent=dam, alignment=TA_RIGHT)
    tieu_de = ParagraphStyle(
        "tieu_de", parent=dam, fontSize=17, leading=21, textColor=xanh, alignment=TA_RIGHT
    )
    thuong_hieu = ParagraphStyle("thuong_hieu", parent=dam, fontSize=14, leading=18, textColor=xanh)

    def p(van_ban, kieu=chu):
        return Paragraph(escape(str(van_ban)).replace("\n", "<br/>"), kieu)

    dem = BytesIO()
    phieu, chi_nhanh = du_lieu["phieu"], du_lieu["chi_nhanh"]
    tai_lieu = SimpleDocTemplate(
        dem,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Hóa đơn {phieu.ma_phieu_ban}",
        author=du_lieu["ten_thuong_hieu"],
    )
    rong = A4[0] - 32 * mm
    lien_he = chi_nhanh.dia_chi + (
        f"\nĐiện thoại: {chi_nhanh.so_dien_thoai}" if chi_nhanh.so_dien_thoai else ""
    )
    dau = Table(
        [
            [
                [
                    p(du_lieu["ten_thuong_hieu"], thuong_hieu),
                    p(chi_nhanh.ten_chi_nhanh, dam),
                    p(lien_he, nho),
                ],
                [
                    p("HÓA ĐƠN BÁN LẺ", tieu_de),
                    p(f"Số: {phieu.ma_phieu_ban}", phai),
                    p(du_lieu["thoi_diem"].strftime("Ngày %d/%m/%Y lúc %H:%M"), phai),
                ],
            ]
        ],
        colWidths=[rong * 0.55, rong * 0.45],
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
    khach = du_lieu["khach"]
    dong_khach = [f"Khách hàng: {khach['ten']}"]
    if khach["so_dien_thoai"]:
        dong_khach.append(f"Điện thoại: {khach['so_dien_thoai']}")
    if khach["dia_chi"]:
        dong_khach.append(f"Giao đến: {khach['dia_chi']}")
    if du_lieu["don"]:
        dong_khach.append(f"Đơn hàng: {du_lieu['don'].ma_don_hang}")
    dong_khach.append(f"Người bán: {du_lieu['nguoi_ban']}")

    hang = [
        [
            p("STT", dam),
            p("Tên thuốc", dam),
            p("ĐVT", dam),
            p("SL", phai_dam),
            p("Đơn giá", phai_dam),
            p("Thành tiền", phai_dam),
        ]
    ]
    for dong in du_lieu["cac_dong"]:
        ten = [p(dong["ten"] + (" (thuốc kê đơn)" if dong["ke_don"] else ""))]
        if dong["cac_lo"]:
            ten.append(
                p(
                    " · ".join(
                        f"Lô {lo['ma']}, HSD {lo['han_dung']:%d/%m/%Y}" for lo in dong["cac_lo"]
                    ),
                    nho,
                )
            )
        hang.append(
            [
                p(dong["stt"]),
                ten,
                p(dong["don_vi"]),
                p(dong["so_luong"], phai),
                p(_tien(dong["don_gia"]), phai),
                p(_tien(dong["thanh_tien"]), phai),
            ]
        )
    bang = Table(
        hang, colWidths=[rong * w for w in (0.07, 0.43, 0.1, 0.08, 0.15, 0.17)], repeatRows=1
    )
    bang.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, xanh),
                ("LINEBELOW", (0, 1), (-1, -1), 0.4, vien),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    tong = du_lieu["tong"]
    cac_tong = [[p("Tiền hàng"), p(_tien(tong["tien_hang"]), phai)]]
    if tong["giam_gia"]:
        cac_tong.append([p("Ưu đãi thành viên"), p("-" + _tien(tong["giam_gia"]), phai)])
    if du_lieu["don"] and du_lieu["don"].la_giao_hang:
        cac_tong.append([p("Phí giao hàng"), p(_tien(tong["phi_giao"]), phai)])
    cac_tong.append([p("Tổng thanh toán", dam), p(_tien(tong["tong"]), phai_dam)])
    bang_tong = Table(cac_tong, colWidths=[rong * 0.22, rong * 0.2], hAlign="RIGHT")
    bang_tong.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, -1), (-1, -1), 0.8, xanh),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    noi_dung = [
        dau,
        Spacer(1, 7 * mm),
        p("\n".join(dong_khach)),
        Spacer(1, 5 * mm),
        bang,
        Spacer(1, 4 * mm),
        bang_tong,
        Spacer(1, 2 * mm),
        p(f"Bằng chữ: {du_lieu['bang_chu']}.", dam),
        Spacer(1, 3 * mm),
    ]
    for khoan in du_lieu["cac_khoan"]:
        nhan = "Đã hoàn" if khoan.loai_giao_dich == "hoan" else "Đã thu"
        noi_dung.append(
            p(
                f"{nhan} {_tien(khoan.so_tien)} · {khoan.get_phuong_thuc_display()} · "
                f"{timezone.localtime(khoan.thoi_diem_hoan_tat):%H:%M %d/%m/%Y}",
                nho,
            )
        )
    if du_lieu["con_phai_thu"]:
        noi_dung.append(p(f"Còn phải thu: {_tien(du_lieu['con_phai_thu'])}", dam))
    if phieu.da_kiem_tra_don_thuoc:
        noi_dung += [
            Spacer(1, 3 * mm),
            p(
                f"Bán theo đơn của {phieu.ten_nguoi_ke_don}, {phieu.noi_kham_benh}"
                + (f", mã đơn {phieu.ma_don_thuoc}" if phieu.ma_don_thuoc else "")
                + ".",
                nho,
            ),
        ]
    if du_lieu["da_hoan_kho"]:
        noi_dung += [Spacer(1, 3 * mm), p("Phiếu bán đã hoàn kho do đơn bị hủy.", dam)]
    noi_dung += [
        Spacer(1, 8 * mm),
        p("Cảm ơn quý khách. Vui lòng đọc kỹ hướng dẫn sử dụng trước khi dùng thuốc.", chu),
        Spacer(1, 2 * mm),
        p(du_lieu["ghi_chu_phap_ly"], nho),
    ]
    tai_lieu.build(noi_dung)
    return dem.getvalue()
