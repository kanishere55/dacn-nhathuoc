"""Đọc kết quả thực nghiệm dự báo để hiển thị: tổng quan tám nhóm ATC và chi tiết từng nhóm."""

from collections import Counter, defaultdict

from django.db.models import Avg, Count, F, Max, Min
from django.db.models.functions import ExtractIsoWeekDay, ExtractMonth, TruncMonth

from ung_dung.danh_muc.models import NhomATC

from .models import DuBaoBayNgay, KetQuaMoHinh, KichBanThieuHang, LanThucNghiem, QuanSatBanHang

# Thứ tự cố định khi vẽ và so sánh; tên hiển thị của mã mô hình lưu trong ket_qua_mo_hinh.mo_hinh.
TEN_MO_HINH = {
    "hoi_quy_tuyen_tinh": "Hồi quy tuyến tính",
    "cay_quyet_dinh": "Cây quyết định",
    "rung_ngau_nhien": "Rừng ngẫu nhiên",
    "xgboost": "XGBoost",
    "sarimax": "SARIMAX",
}
LOAI_MO_HINH = {
    "hoi_quy_tuyen_tinh": "Học máy",
    "cay_quyet_dinh": "Học máy",
    "rung_ngau_nhien": "Học máy",
    "xgboost": "Học máy",
    "sarimax": "Chuỗi thời gian",
}
TEN_DAC_TRUNG = {
    "ngay_hien_tai": "Lượng bán ngày gốc",
    "ngay_truoc": "Lượng bán ngày liền trước",
    "tuan_truoc": "Lượng bán cùng thứ tuần trước",
    "trung_binh_7": "Trung bình trượt 7 ngày",
    "trung_binh_28": "Trung bình trượt 28 ngày",
    "thu": "Thứ trong tuần",
    "thang": "Tháng trong năm",
}


def lan_moi_nhat():
    return LanThucNghiem.objects.select_related("nguon_du_lieu").order_by("-pk").first()


def _ten_nhom(cac_ma):
    return dict(
        NhomATC.objects.filter(ma_nhom_atc__in=cac_ma).values_list("ma_nhom_atc", "ten_nhom_atc")
    )


def _thong_tin_mo_hinh(dong):
    return {
        "ma": dong.mo_hinh,
        "ten": TEN_MO_HINH.get(dong.mo_hinh, dong.mo_hinh),
        "loai": LOAI_MO_HINH.get(dong.mo_hinh, ""),
        "mae_xac_thuc": dong.mae_xac_thuc,
        "rmse_xac_thuc": dong.rmse_xac_thuc,
        "mae_kiem_thu": dong.mae_kiem_thu,
        "rmse_kiem_thu": dong.rmse_kiem_thu,
        "duoc_chon": dong.duoc_chon,
    }


def _thu_tu_mo_hinh(ma):
    return list(TEN_MO_HINH).index(ma) if ma in TEN_MO_HINH else len(TEN_MO_HINH)


def lay_ket_qua_moi_nhat():
    lan = lan_moi_nhat()
    if lan is None:
        return {"lan": None}
    cac_ket_qua = KetQuaMoHinh.objects.filter(lan_thuc_nghiem=lan)
    theo_nhom = defaultdict(list)
    for dong in cac_ket_qua:
        theo_nhom[dong.ma_atc_nguon].append(dong)
    cac_ma = sorted(theo_nhom)
    ten_nhom = _ten_nhom(cac_ma)
    # Trung bình tổng bảy ngày thực tế trên tập kiểm thử: mẫu số để đổi MAE thành tỷ lệ sai số.
    trung_binh = dict(
        DuBaoBayNgay.objects.filter(
            ket_qua_mo_hinh__lan_thuc_nghiem=lan,
            ket_qua_mo_hinh__duoc_chon=True,
            ky_danh_gia="kiem_thu",
        )
        .values_list("ket_qua_mo_hinh__ma_atc_nguon")
        .annotate(tb=Avg("so_luong_thuc_te"))
    )
    tuong_lai = {
        d.ket_qua_mo_hinh.ma_atc_nguon: d
        for d in DuBaoBayNgay.objects.filter(
            ket_qua_mo_hinh__lan_thuc_nghiem=lan, ky_danh_gia="tuong_lai"
        ).select_related("ket_qua_mo_hinh")
    }
    sarimax = (lan.cau_hinh or {}).get("sarimax_theo_nhom", {})
    cac_nhom = []
    for ma in cac_ma:
        cac_mo_hinh = sorted(
            (_thong_tin_mo_hinh(d) for d in theo_nhom[ma]), key=lambda m: _thu_tu_mo_hinh(m["ma"])
        )
        chon = next((m for m in cac_mo_hinh if m["duoc_chon"]), None)
        if chon is None:
            continue
        tot_nhat_test = min(m["mae_kiem_thu"] for m in cac_mo_hinh)
        tb = trung_binh.get(ma) or 0
        du_bao = tuong_lai.get(ma)
        ty_le = chon["mae_kiem_thu"] / tb * 100 if tb else None
        cac_nhom.append(
            {
                "ma": ma,
                "ten": ten_nhom.get(ma, ""),
                "chon": chon,
                "cac_mo_hinh": [
                    {**m, "tot_nhat_test": m["mae_kiem_thu"] == tot_nhat_test} for m in cac_mo_hinh
                ],
                "trung_binh_7_ngay": tb,
                "ty_le_sai_so": ty_le,
                "muc_sai_so": _muc_sai_so(ty_le),
                "du_bao": du_bao,
                "sarimax": sarimax.get(ma, {}).get("tham_so_chon"),
            }
        )
    nguon = QuanSatBanHang.objects.filter(nguon_du_lieu=lan.nguon_du_lieu).aggregate(
        so_quan_sat=Count("pk"), tu_ngay=Min("ngay_ban"), den_ngay=Max("ngay_ban")
    )
    dem_chon = Counter(n["chon"]["ten"] for n in cac_nhom).most_common() or [("–", 0)]
    return {
        "lan": lan,
        "nguon": nguon,
        "cac_nhom": cac_nhom,
        "dem_chon": dem_chon,
        "so_mo_hinh": len(TEN_MO_HINH),
        "giai_doan": _giai_doan(lan, nguon["tu_ngay"]),
        "dac_trung": [
            TEN_DAC_TRUNG.get(ma, ma) for ma in (lan.cau_hinh or {}).get("dac_trung", [])
        ],
        "thu_vien": (lan.cau_hinh or {}).get("thu_vien", {}),
        "cac_kich_ban": KichBanThieuHang.objects.filter(
            du_bao_bay_ngay__ket_qua_mo_hinh__lan_thuc_nghiem=lan
        )
        .select_related("du_bao_bay_ngay__ket_qua_mo_hinh")
        .annotate(
            kha_dung=F("so_luong_ton") - F("so_luong_dang_giu"),
            chenh_lech=F("so_luong_ton")
            - F("so_luong_dang_giu")
            - F("so_luong_du_tru")
            - F("du_bao_bay_ngay__so_luong_du_bao"),
        )
        .order_by("-pk")[:20],
    }


def _muc_sai_so(ty_le):
    """Xếp mức sai số tương đối (MAE / trung bình tổng 7 ngày) để tô màu thẻ kết quả."""
    if ty_le is None:
        return ""
    if ty_le < 20:
        return "thap"
    return "vua" if ty_le < 35 else "cao"


def _giai_doan(lan, tu_ngay):
    """Ba đoạn huấn luyện / xác thực / kiểm thử với độ rộng theo số ngày để vẽ dải thời gian."""
    if tu_ngay is None:
        return []
    cac_moc = [
        ("huan_luyen", "Huấn luyện", tu_ngay, lan.ngay_chot_huan_luyen),
        ("xac_thuc", "Xác thực", lan.ngay_chot_huan_luyen, lan.ngay_chot_xac_thuc),
        ("kiem_thu", "Kiểm thử", lan.ngay_chot_xac_thuc, lan.ngay_chot_kiem_thu),
    ]
    tong = max((lan.ngay_chot_kiem_thu - tu_ngay).days, 1)
    return [
        {
            "ma": ma,
            "ten": ten,
            "tu": dau,
            "den": cuoi,
            "ty_le": round((cuoi - dau).days / tong * 100, 2),
        }
        for ma, ten, dau, cuoi in cac_moc
    ]


def lay_chi_tiet_nhom(lan, ma_atc):
    """Dữ liệu biểu đồ của một nhóm ATC; None khi lần thực nghiệm không có nhóm này."""
    cac_ket_qua = list(KetQuaMoHinh.objects.filter(lan_thuc_nghiem=lan, ma_atc_nguon=ma_atc))
    if not cac_ket_qua:
        return None
    cac_ket_qua.sort(key=lambda d: _thu_tu_mo_hinh(d.mo_hinh))
    quan_sat = QuanSatBanHang.objects.filter(
        nguon_du_lieu=lan.nguon_du_lieu, ma_atc_nguon=ma_atc
    ).order_by()
    theo_thang = (
        quan_sat.annotate(thang=TruncMonth("ngay_ban"))
        .values("thang")
        .annotate(tb=Avg("so_luong"), so_ngay=Count("pk"))
        .order_by("thang")
    )
    mua_vu = (
        quan_sat.annotate(thang=ExtractMonth("ngay_ban"))
        .values("thang")
        .annotate(tb=Avg("so_luong"))
        .order_by("thang")
    )
    theo_thu = (
        quan_sat.annotate(thu=ExtractIsoWeekDay("ngay_ban"))
        .values("thu")
        .annotate(tb=Avg("so_luong"))
        .order_by("thu")
    )
    kiem_thu = DuBaoBayNgay.objects.filter(
        ket_qua_mo_hinh__in=cac_ket_qua, ky_danh_gia="kiem_thu"
    ).values_list("ket_qua_mo_hinh__mo_hinh", "ngay_goc", "so_luong_du_bao", "so_luong_thuc_te")
    cac_ngay, thuc_te, du_bao = [], {}, defaultdict(dict)
    for mo_hinh, ngay, gia_tri, that in kiem_thu.order_by("ngay_goc"):
        if ngay not in thuc_te:
            cac_ngay.append(ngay)
            thuc_te[ngay] = that
        du_bao[mo_hinh][ngay] = gia_tri
    chon = next(d for d in cac_ket_qua if d.duoc_chon)
    tuong_lai = DuBaoBayNgay.objects.filter(ket_qua_mo_hinh=chon, ky_danh_gia="tuong_lai").first()
    return {
        "ma": ma_atc,
        "ten": _ten_nhom([ma_atc]).get(ma_atc, ""),
        "mo_hinh_chon": chon.mo_hinh,
        "cac_mo_hinh": [_thong_tin_mo_hinh(d) for d in cac_ket_qua],
        "moc": {
            "huan_luyen": lan.ngay_chot_huan_luyen,
            "xac_thuc": lan.ngay_chot_xac_thuc,
            "kiem_thu": lan.ngay_chot_kiem_thu,
        },
        "theo_thang": [
            {"thang": d["thang"].strftime("%Y-%m"), "tb": d["tb"], "so_ngay": d["so_ngay"]}
            for d in theo_thang
        ],
        "mua_vu": [{"thang": d["thang"], "tb": d["tb"]} for d in mua_vu],
        "theo_thu": [{"thu": d["thu"], "tb": d["tb"]} for d in theo_thu],
        "kiem_thu": {
            "ngay": [n.isoformat() for n in cac_ngay],
            "thuc_te": [thuc_te[n] for n in cac_ngay],
            "du_bao": {
                d.mo_hinh: [du_bao[d.mo_hinh].get(n) for n in cac_ngay] for d in cac_ket_qua
            },
        },
        "tuong_lai": (
            {
                "ngay_goc": tuong_lai.ngay_goc,
                "so_luong": tuong_lai.so_luong_du_bao,
                "mae": chon.mae_kiem_thu,
            }
            if tuong_lai
            else None
        ),
    }
