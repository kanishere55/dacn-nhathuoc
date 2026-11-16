"""Sổ nhập – xuất – tồn suy ra từ chứng từ, dùng chung cho báo cáo và lệnh đối chiếu.

Mỗi nguồn biến động là một loại dòng chứng từ làm đổi tồn (Q06: tồn chỉ đổi qua chứng từ):
(nhóm, dấu, tập dòng, đường tới chi nhánh, đường tới lô, đường tới thời điểm, biểu thức lượng).
Cộng có dấu mọi nguồn theo (chi nhánh, lô) từ trước tới nay phải bằng ton_kho.so_luong.
"""

from django.db.models import F, Sum

from .models import (
    ChiTietPhieuDieuChuyen,
    ChiTietPhieuKiemKe,
    ChiTietPhieuNhap,
    ChiTietPhieuTraNhaCungCap,
    ChiTietPhieuXuatHuy,
    TonKho,
)

# Thứ tự cột trên báo cáo: các cột cộng trước, các cột trừ sau.
NHOM_BIEN_DONG = (
    ("nhap", "Nhập", 1),
    ("chuyen_den", "Chuyển đến", 1),
    ("dieu_chinh", "Điều chỉnh kiểm kê", 1),
    ("ban", "Bán", -1),
    ("chuyen_di", "Chuyển đi", -1),
    ("tra", "Trả NCC", -1),
    ("xuat_huy", "Xuất hủy", -1),
)
DAU = {ma: dau for ma, _, dau in NHOM_BIEN_DONG}


def cac_nguon_bien_dong():
    from ung_dung.ban_hang.models import PhanBoPhieuBan

    luong = F("so_luong")
    return [
        (
            "nhap",
            ChiTietPhieuNhap.objects.all(),
            "phieu_nhap__chi_nhanh",
            "lo_thuoc",
            "phieu_nhap__thoi_diem_tao",
            luong,
        ),
        (
            "ban",
            PhanBoPhieuBan.objects.all(),
            "ton_kho__chi_nhanh",
            "ton_kho__lo_thuoc",
            "chi_tiet_phieu_ban__phieu_ban__thoi_diem_tao",
            luong,
        ),
        (
            "tra",
            ChiTietPhieuTraNhaCungCap.objects.all(),
            "phieu_tra_nha_cung_cap__phieu_nhap__chi_nhanh",
            "lo_thuoc",
            "phieu_tra_nha_cung_cap__thoi_diem_tao",
            luong,
        ),
        (
            "chuyen_di",
            ChiTietPhieuDieuChuyen.objects.all(),
            "phieu_dieu_chuyen__chi_nhanh_nguon",
            "lo_thuoc",
            "phieu_dieu_chuyen__thoi_diem_tao",
            luong,
        ),
        (
            "chuyen_den",
            ChiTietPhieuDieuChuyen.objects.all(),
            "phieu_dieu_chuyen__chi_nhanh_dich",
            "lo_thuoc",
            "phieu_dieu_chuyen__thoi_diem_tao",
            luong,
        ),
        (
            "dieu_chinh",
            ChiTietPhieuKiemKe.objects.all(),
            "phieu_kiem_ke__chi_nhanh",
            "lo_thuoc",
            "phieu_kiem_ke__thoi_diem_tao",
            F("so_luong_thuc_te") - F("so_luong_so_sach"),
        ),
        (
            "xuat_huy",
            ChiTietPhieuXuatHuy.objects.all(),
            "phieu_xuat_huy__chi_nhanh",
            "lo_thuoc",
            "phieu_xuat_huy__thoi_diem_tao",
            luong,
        ),
    ]


def bien_dong_theo(nhom_theo, *, cac_chi_nhanh=None, tu_luc=None, den_luc=None):
    """{khóa nhóm: {mã biến động: tổng lượng (dương)}} của các chứng từ trong khoảng thời gian.

    `nhom_theo(duong_chi_nhanh, duong_lo)` trả danh sách đường dẫn dùng để gộp, ví dụ đơn vị
    tính hoặc (chi nhánh, lô). Khóa nhóm là bộ giá trị theo đúng thứ tự đó.
    """
    ket_qua = {}
    for ma, tap_hop, duong_cn, duong_lo, duong_luc, bieu_thuc in cac_nguon_bien_dong():
        if cac_chi_nhanh is not None:
            tap_hop = tap_hop.filter(**{f"{duong_cn}__in": cac_chi_nhanh})
        if tu_luc is not None:
            tap_hop = tap_hop.filter(**{f"{duong_luc}__gte": tu_luc})
        if den_luc is not None:
            tap_hop = tap_hop.filter(**{f"{duong_luc}__lt": den_luc})
        cac_cot = nhom_theo(duong_cn, duong_lo)
        for dong in tap_hop.order_by().values(*cac_cot).annotate(tong=Sum(bieu_thuc)):
            nhom = ket_qua.setdefault(tuple(dong[cot] for cot in cac_cot), {})
            nhom[ma] = nhom.get(ma, 0) + (dong["tong"] or 0)
    return ket_qua


def tong_co_dau(bien_dong):
    return sum(DAU[ma] * luong for ma, luong in bien_dong.items())


def doi_chieu_ton_kho(cac_chi_nhanh=None):
    """Các dòng tồn lệch sổ: [(tồn kho, số theo chứng từ)]; danh sách rỗng là khớp hoàn toàn.

    Chỉ đọc. So ton_kho.so_luong với Σ(nhập + chuyển đến + hoàn kho + nhập lại + điều chỉnh)
    − Σ(bán + chuyển đi + trả NCC + xuất hủy) theo từng (chi nhánh, lô).
    """
    theo_lo = bien_dong_theo(
        lambda duong_cn, duong_lo: [duong_cn, duong_lo],
        cac_chi_nhanh=cac_chi_nhanh,
    )
    so_theo_chung_tu = {khoa: tong_co_dau(bd) for khoa, bd in theo_lo.items()}
    cac_ton = TonKho.objects.select_related("chi_nhanh", "lo_thuoc__thuoc").order_by(
        "chi_nhanh__ma_chi_nhanh", "lo_thuoc__thuoc__ten_thuoc", "lo_thuoc__ma_lo_thuoc"
    )
    if cac_chi_nhanh is not None:
        cac_ton = cac_ton.filter(chi_nhanh__in=cac_chi_nhanh)
    lech = []
    da_xet = set()
    for ton in cac_ton:
        khoa = (ton.chi_nhanh_id, ton.lo_thuoc_id)
        da_xet.add(khoa)
        theo_chung_tu = so_theo_chung_tu.get(khoa, 0)
        if theo_chung_tu != ton.so_luong:
            lech.append((ton, theo_chung_tu))
    # Chứng từ nhắc tới (chi nhánh, lô) chưa có dòng tồn: cũng là lệch nếu tổng khác 0.
    for khoa, tong in so_theo_chung_tu.items():
        if khoa not in da_xet and tong:
            lech.append((TonKho(chi_nhanh_id=khoa[0], lo_thuoc_id=khoa[1], so_luong=0), tong))
    return lech
