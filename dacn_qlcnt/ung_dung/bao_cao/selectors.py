from datetime import datetime, time, timedelta

from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value, When
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from ung_dung.ban_hang.models import PHUONG_THUC_TAI_QUAY, ChiTietPhieuBan, DonHang, PhieuBan
from ung_dung.chung.permissions import kiem_tra_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh
from ung_dung.kho.doi_chieu import NHOM_BIEN_DONG, bien_dong_theo, tong_co_dau
from ung_dung.kho.models import (
    PhieuDieuChuyen,
    PhieuKiemKe,
    PhieuNhap,
    PhieuTraNhaCungCap,
    PhieuXuatHuy,
    TonKho,
)
from ung_dung.kho.selectors import lay_ton_kha_dung


def lay_bao_cao(nguoi, tu_ngay, den_ngay, chi_nhanh=None):
    kiem_tra_quyen(nguoi, "bao_cao.xem")
    tu_luc = timezone.make_aware(datetime.combine(tu_ngay, time.min))
    den_luc = timezone.make_aware(datetime.combine(den_ngay + timedelta(days=1), time.min))
    cac_chi_nhanh = lay_chi_nhanh(nguoi, ca_chi_nhanh_ngung=True)
    if chi_nhanh is not None:
        cac_chi_nhanh = cac_chi_nhanh.filter(pk=chi_nhanh.pk)
    trong_ky = {"thoi_diem_tao__gte": tu_luc, "thoi_diem_tao__lt": den_luc}

    phieu_nhap = PhieuNhap.objects.filter(chi_nhanh__in=cac_chi_nhanh, **trong_ky)
    phieu_ban = PhieuBan.objects.filter(chi_nhanh__in=cac_chi_nhanh, **trong_ky)
    phieu_tra = PhieuTraNhaCungCap.objects.filter(
        phieu_nhap__chi_nhanh__in=cac_chi_nhanh, **trong_ky
    )
    phieu_kiem_ke = PhieuKiemKe.objects.filter(chi_nhanh__in=cac_chi_nhanh, **trong_ky)
    phieu_chuyen = PhieuDieuChuyen.objects.filter(
        Q(chi_nhanh_nguon__in=cac_chi_nhanh) | Q(chi_nhanh_dich__in=cac_chi_nhanh), **trong_ky
    )
    don = DonHang.objects.filter(chi_nhanh__in=cac_chi_nhanh, **trong_ky)
    phieu_xuat_huy = PhieuXuatHuy.objects.filter(chi_nhanh__in=cac_chi_nhanh, **trong_ky)
    dong_ban = ChiTietPhieuBan.objects.filter(phieu_ban__in=phieu_ban)
    tien = ExpressionWrapper(
        F("so_luong") * F("don_gia") - F("giam_gia_phan_bo"),
        output_field=DecimalField(),
    )
    cac_luong = bang_nhap_xuat_ton(cac_chi_nhanh, tu_luc, den_luc)
    # Mỗi phiếu bán là một lần khách nhận thuốc và trả đủ tiền tại quầy (bán trực tiếp hoặc
    # nhận đơn đặt giữ), nên doanh thu tính theo kỳ lập phiếu, sau ưu đãi thành viên.
    doanh_thu = dong_ban.aggregate(tong=Sum(tien, default=0))["tong"]
    ten_phuong_thuc = dict(PHUONG_THUC_TAI_QUAY)
    theo_phuong_thuc = [
        (ten_phuong_thuc.get(d["phieu_ban__phuong_thuc_thanh_toan"], ""), d["tong"])
        for d in dong_ban.values("phieu_ban__phuong_thuc_thanh_toan")
        .annotate(tong=Sum(tien))
        .order_by("-tong")
    ]
    ban_chay = list(
        dong_ban.values(
            "thuoc__ma_thuoc", "thuoc__ten_thuoc", "thuoc__don_vi_tinh__ten_don_vi_tinh"
        )
        .annotate(doanh_thu=Sum(tien), tong_so_luong=Sum("so_luong"))
        .order_by("-doanh_thu")[:10]
    )
    so_phieu_ban = phieu_ban.count()
    # Kỳ liền trước cùng độ dài, để so sánh doanh thu tăng hay giảm.
    so_ngay = (den_ngay - tu_ngay).days + 1
    phieu_ky_truoc = PhieuBan.objects.filter(
        chi_nhanh__in=cac_chi_nhanh,
        thoi_diem_tao__gte=tu_luc - timedelta(days=so_ngay),
        thoi_diem_tao__lt=tu_luc,
    )
    doanh_thu_ky_truoc = ChiTietPhieuBan.objects.filter(phieu_ban__in=phieu_ky_truoc).aggregate(
        tong=Sum(tien, default=0)
    )["tong"]
    return {
        "bieu_do": _du_lieu_bieu_do(dong_ban, tien, tu_ngay, den_ngay, theo_phuong_thuc, ban_chay),
        "doanh_thu_ky_truoc": doanh_thu_ky_truoc,
        "thay_doi_doanh_thu": (
            (doanh_thu - doanh_thu_ky_truoc) / doanh_thu_ky_truoc * 100
            if doanh_thu_ky_truoc
            else None
        ),
        "doanh_thu": doanh_thu,
        "trung_binh_phieu": doanh_thu / so_phieu_ban if so_phieu_ban else 0,
        "theo_phuong_thuc": theo_phuong_thuc,
        "ban_chay": ban_chay,
        "so_phieu_nhap": phieu_nhap.count(),
        "so_phieu_ban": so_phieu_ban,
        "so_phieu_tra": phieu_tra.count(),
        "so_phieu_kiem_ke": phieu_kiem_ke.count(),
        "so_phieu_chuyen": phieu_chuyen.count(),
        "so_phieu_xuat_huy": phieu_xuat_huy.count(),
        "so_don_giu": don.count(),
        "so_don_da_nhan": don.filter(trang_thai="hoan_thanh").count(),
        "cac_luong": sorted(cac_luong.items()),
        "cot_bien_dong": COT_BIEN_DONG,
        "bang_bien_dong": [
            (don_vi, [dong.get(ma, 0) or 0 for ma, _ in COT_BIEN_DONG])
            for don_vi, dong in sorted(cac_luong.items())
        ],
    }


# Cột của bảng nhập – xuất – tồn theo kỳ (web và Excel dùng chung):
# tồn đầu kỳ + các cột cộng − các cột trừ = tồn cuối kỳ; khả dụng là số hiện tại, không theo kỳ.
COT_BIEN_DONG = [
    ("ton_dau", "Tồn đầu kỳ"),
    *((ma, nhan) for ma, nhan, _ in NHOM_BIEN_DONG),
    ("ton_cuoi", "Tồn cuối kỳ"),
    ("kha_dung", "Khả dụng hiện tại"),
]


def bang_nhap_xuat_ton(cac_chi_nhanh, tu_luc, den_luc):
    """{đơn vị: {mã cột: lượng}} theo đơn vị cơ sở, tính từ chứng từ (kho/doi_chieu.py).

    Tồn cuối kỳ = tồn vật lý hiện tại − biến động sau kỳ; tồn đầu kỳ = tồn cuối − biến động
    trong kỳ. Bán là toàn bộ hàng đã xuất bán tại quầy.
    """
    don_vi = "lo_thuoc__thuoc__don_vi_tinh__ten_don_vi_tinh"

    def theo_don_vi(_duong_cn, duong_lo):
        return [f"{duong_lo}__thuoc__don_vi_tinh__ten_don_vi_tinh"]

    trong_ky = bien_dong_theo(
        theo_don_vi, cac_chi_nhanh=cac_chi_nhanh, tu_luc=tu_luc, den_luc=den_luc
    )
    sau_ky = bien_dong_theo(theo_don_vi, cac_chi_nhanh=cac_chi_nhanh, tu_luc=den_luc)
    hien_tai = dict(
        TonKho.objects.filter(chi_nhanh__in=cac_chi_nhanh)
        .order_by()
        .values_list(don_vi)
        .annotate(tong=Sum("so_luong"))
    )
    kha_dung = dict(
        lay_ton_kha_dung()
        .filter(chi_nhanh__in=cac_chi_nhanh)
        .order_by()
        .values_list(don_vi)
        .annotate(tong=Sum("kha_dung"))
    )
    ket_qua = {}
    for ten in {*hien_tai, *(k[0] for k in trong_ky), *(k[0] for k in sau_ky)}:
        dong = dict(trong_ky.get((ten,), {}))
        dong["ton_cuoi"] = (hien_tai.get(ten) or 0) - tong_co_dau(sau_ky.get((ten,), {}))
        dong["ton_dau"] = dong["ton_cuoi"] - tong_co_dau(trong_ky.get((ten,), {}))
        dong["kha_dung"] = kha_dung.get(ten) or 0
        if any(dong.values()):
            ket_qua[ten] = dong
    return ket_qua


KENH_BAN = Case(
    When(phieu_ban__don_hang__isnull=True, then=Value("Bán trực tiếp tại quầy")),
    default=Value("Đặt giữ trên website"),
)


def _du_lieu_bieu_do(dong_ban, tien, tu_ngay, den_ngay, theo_phuong_thuc, ban_chay):
    """Số liệu cho các biểu đồ báo cáo; kỳ dài hơn 92 ngày gộp theo tháng cho dễ đọc."""
    theo_thang = (den_ngay - tu_ngay).days > 92
    truc = TruncMonth if theo_thang else TruncDate
    # TruncMonth trên cột thời điểm trả về datetime; đưa về date để khớp với các mốc đã sinh.
    theo_moc = {
        (dong["moc"].date() if isinstance(dong["moc"], datetime) else dong["moc"]): dong
        for dong in dong_ban.annotate(moc=truc("phieu_ban__thoi_diem_tao"))
        .values("moc")
        .annotate(tong=Sum(tien), so_phieu=Count("phieu_ban", distinct=True))
        .order_by()
    }
    cac_moc = []
    ngay = tu_ngay.replace(day=1) if theo_thang else tu_ngay
    while ngay <= den_ngay:
        cac_moc.append(ngay)
        ngay = (
            (ngay.replace(day=28) + timedelta(days=4)).replace(day=1)
            if theo_thang
            else ngay + timedelta(days=1)
        )
    return {
        "don_vi_thoi_gian": "thang" if theo_thang else "ngay",
        "theo_thoi_gian": [
            {
                "moc": m.isoformat(),
                "doanh_thu": float(theo_moc.get(m, {}).get("tong") or 0),
                "so_phieu": theo_moc.get(m, {}).get("so_phieu") or 0,
            }
            for m in cac_moc
        ],
        "theo_chi_nhanh": [
            {"ten": d["phieu_ban__chi_nhanh__ten_chi_nhanh"], "doanh_thu": float(d["tong"])}
            for d in dong_ban.values("phieu_ban__chi_nhanh__ten_chi_nhanh")
            .annotate(tong=Sum(tien))
            .order_by("-tong")
        ],
        "theo_kenh": [
            {"ten": d["kenh"], "doanh_thu": float(d["tong"])}
            for d in dong_ban.annotate(kenh=KENH_BAN)
            .values("kenh")
            .annotate(tong=Sum(tien))
            .order_by("-tong")
        ],
        "theo_phuong_thuc": [
            {"ten": ten, "so_tien": float(tien_)} for ten, tien_ in theo_phuong_thuc
        ],
        "ban_chay": [
            {
                "ten": d["thuoc__ten_thuoc"],
                "doanh_thu": float(d["doanh_thu"]),
                "so_luong": d["tong_so_luong"],
                "don_vi": d["thuoc__don_vi_tinh__ten_don_vi_tinh"],
            }
            for d in ban_chay
        ],
    }
