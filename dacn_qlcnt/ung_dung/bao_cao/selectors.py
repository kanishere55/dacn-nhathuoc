from datetime import datetime, time, timedelta

from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value, When
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from ung_dung.ban_hang.models import ChiTietPhieuBan, DonHang, PhieuBan, PhieuHoanKho
from ung_dung.chung.permissions import kiem_tra_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh
from ung_dung.kho.models import (
    ChiTietPhieuDieuChuyen,
    ChiTietPhieuKiemKe,
    ChiTietPhieuNhap,
    ChiTietPhieuTraNhaCungCap,
    PhieuDieuChuyen,
    PhieuKiemKe,
    PhieuNhap,
    PhieuTraNhaCungCap,
)
from ung_dung.kho.selectors import lay_ton_kha_dung
from ung_dung.thanh_toan.models import PHUONG_THUC, GiaoDichThanhToan


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
    chuyen_di = PhieuDieuChuyen.objects.filter(chi_nhanh_nguon__in=cac_chi_nhanh, **trong_ky)
    chuyen_den = PhieuDieuChuyen.objects.filter(chi_nhanh_dich__in=cac_chi_nhanh, **trong_ky)
    phieu_chuyen = PhieuDieuChuyen.objects.filter(
        Q(chi_nhanh_nguon__in=cac_chi_nhanh) | Q(chi_nhanh_dich__in=cac_chi_nhanh), **trong_ky
    )
    don = DonHang.objects.filter(chi_nhanh__in=cac_chi_nhanh, **trong_ky)
    dong_ban = ChiTietPhieuBan.objects.filter(phieu_ban__in=phieu_ban)
    tien = ExpressionWrapper(F("so_luong") * F("don_gia"), output_field=DecimalField())
    cac_luong = {}
    cac_nhom = [
        (
            "nhap",
            ChiTietPhieuNhap.objects.filter(phieu_nhap__in=phieu_nhap),
            "lo_thuoc__thuoc",
            "so_luong",
        ),
        ("ban", dong_ban, "thuoc", "so_luong"),
        (
            "tra",
            ChiTietPhieuTraNhaCungCap.objects.filter(phieu_tra_nha_cung_cap__in=phieu_tra),
            "lo_thuoc__thuoc",
            "so_luong",
        ),
        (
            "chuyen_di",
            ChiTietPhieuDieuChuyen.objects.filter(phieu_dieu_chuyen__in=chuyen_di),
            "lo_thuoc__thuoc",
            "so_luong",
        ),
        (
            "chuyen_den",
            ChiTietPhieuDieuChuyen.objects.filter(phieu_dieu_chuyen__in=chuyen_den),
            "lo_thuoc__thuoc",
            "so_luong",
        ),
        (
            "dieu_chinh",
            ChiTietPhieuKiemKe.objects.filter(phieu_kiem_ke__in=phieu_kiem_ke),
            "lo_thuoc__thuoc",
            F("so_luong_thuc_te") - F("so_luong_so_sach"),
        ),
        (
            "kha_dung",
            lay_ton_kha_dung().filter(chi_nhanh__in=cac_chi_nhanh),
            "lo_thuoc__thuoc",
            "kha_dung",
        ),
    ]
    for ten, tap, duong_dan, bieu_thuc in cac_nhom:
        cot = f"{duong_dan}__don_vi_tinh__ten_don_vi_tinh"
        for dong in tap.order_by().values(cot).annotate(tong=Sum(bieu_thuc)):
            cac_luong.setdefault(dong[cot], {})[ten] = dong["tong"]
    # Doanh thu: phiếu bán trong kỳ trừ phiếu đã hoàn kho (đơn hủy sau khi xuất) và tiền
    # hoàn do trả hàng trong kỳ. Tiền hoàn vì hủy đơn không trừ thêm: đơn hủy trước khi
    # xuất chưa có phiếu bán, đơn hủy sau khi xuất đã bị loại qua phiếu hoàn kho.
    hoan_kho = PhieuHoanKho.objects.filter(phieu_ban__in=phieu_ban).values("phieu_ban")
    dong_hop_le = dong_ban.exclude(phieu_ban__in=hoan_kho)
    doanh_thu_gop = dong_hop_le.aggregate(tong=Sum(tien, default=0))["tong"]
    tien_hoan_kho = dong_ban.filter(phieu_ban__in=hoan_kho).aggregate(tong=Sum(tien, default=0))[
        "tong"
    ]
    giao_dich = GiaoDichThanhToan.objects.filter(
        Q(don_hang__chi_nhanh__in=cac_chi_nhanh) | Q(phieu_ban__chi_nhanh__in=cac_chi_nhanh),
        trang_thai="thanh_cong",
        thoi_diem_hoan_tat__gte=tu_luc,
        thoi_diem_hoan_tat__lt=den_luc,
    )
    tien_hoan_khach = giao_dich.filter(loai_giao_dich="hoan").aggregate(
        tong=Sum("so_tien", default=0)
    )["tong"]
    # Trả hàng chỉ nhận trên đơn đã hoàn thành, nên khoản hoàn của đơn hoàn thành là hoàn trả hàng.
    tien_hoan_tra_hang = giao_dich.filter(
        loai_giao_dich="hoan", don_hang__trang_thai="hoan_thanh"
    ).aggregate(tong=Sum("so_tien", default=0))["tong"]
    ten_phuong_thuc = dict(PHUONG_THUC)
    theo_phuong_thuc = [
        (ten_phuong_thuc.get(d["phuong_thuc"], d["phuong_thuc"]), d["tong"])
        for d in giao_dich.filter(loai_giao_dich="thu")
        .values("phuong_thuc")
        .annotate(tong=Sum("so_tien"))
        .order_by("-tong")
    ]
    ban_chay = list(
        dong_hop_le.values(
            "thuoc__ma_thuoc", "thuoc__ten_thuoc", "thuoc__don_vi_tinh__ten_don_vi_tinh"
        )
        .annotate(doanh_thu=Sum(tien), tong_so_luong=Sum("so_luong"))
        .order_by("-doanh_thu")[:10]
    )
    # Kỳ liền trước cùng độ dài, để so sánh doanh thu tăng hay giảm.
    so_ngay = (den_ngay - tu_ngay).days + 1
    phieu_ky_truoc = PhieuBan.objects.filter(
        chi_nhanh__in=cac_chi_nhanh,
        thoi_diem_tao__gte=tu_luc - timedelta(days=so_ngay),
        thoi_diem_tao__lt=tu_luc,
    )
    doanh_thu_ky_truoc = (
        ChiTietPhieuBan.objects.filter(phieu_ban__in=phieu_ky_truoc)
        .exclude(phieu_ban__in=PhieuHoanKho.objects.values("phieu_ban"))
        .aggregate(tong=Sum(tien, default=0))["tong"]
    )
    return {
        "bieu_do": _du_lieu_bieu_do(
            dong_hop_le, tien, tu_ngay, den_ngay, theo_phuong_thuc, ban_chay
        ),
        "doanh_thu_ky_truoc": doanh_thu_ky_truoc,
        "thay_doi_doanh_thu": (
            (doanh_thu_gop - doanh_thu_ky_truoc) / doanh_thu_ky_truoc * 100
            if doanh_thu_ky_truoc
            else None
        ),
        "doanh_thu_gop": doanh_thu_gop,
        "tien_hoan_kho": tien_hoan_kho,
        "tien_hoan_khach": tien_hoan_khach,
        "tien_hoan_tra_hang": tien_hoan_tra_hang,
        "doanh_thu_thuan": doanh_thu_gop - tien_hoan_tra_hang,
        "theo_phuong_thuc": theo_phuong_thuc,
        "ban_chay": ban_chay,
        "so_phieu_nhap": phieu_nhap.count(),
        "so_phieu_ban": phieu_ban.count(),
        "so_phieu_tra": phieu_tra.count(),
        "so_phieu_kiem_ke": phieu_kiem_ke.count(),
        "so_phieu_chuyen": phieu_chuyen.count(),
        "so_don_giu": don.count(),
        "tong_tien_ban": dong_ban.aggregate(tong=Sum(tien, default=0))["tong"],
        "cac_luong": sorted(cac_luong.items()),
    }


KENH_BAN = Case(
    When(phieu_ban__don_hang__isnull=True, then=Value("Bán tại quầy")),
    When(phieu_ban__don_hang__hinh_thuc_nhan="giao_hang", then=Value("Giao tận nơi")),
    default=Value("Đặt giữ, nhận tại quầy"),
)


def _du_lieu_bieu_do(dong_hop_le, tien, tu_ngay, den_ngay, theo_phuong_thuc, ban_chay):
    """Số liệu cho các biểu đồ báo cáo; kỳ dài hơn 92 ngày gộp theo tháng cho dễ đọc."""
    theo_thang = (den_ngay - tu_ngay).days > 92
    truc = TruncMonth if theo_thang else TruncDate
    # TruncMonth trên cột thời điểm trả về datetime; đưa về date để khớp với các mốc đã sinh.
    theo_moc = {
        (dong["moc"].date() if isinstance(dong["moc"], datetime) else dong["moc"]): dong
        for dong in dong_hop_le.annotate(moc=truc("phieu_ban__thoi_diem_tao"))
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
            for d in dong_hop_le.values("phieu_ban__chi_nhanh__ten_chi_nhanh")
            .annotate(tong=Sum(tien))
            .order_by("-tong")
        ],
        "theo_kenh": [
            {"ten": d["kenh"], "doanh_thu": float(d["tong"])}
            for d in dong_hop_le.annotate(kenh=KENH_BAN)
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
