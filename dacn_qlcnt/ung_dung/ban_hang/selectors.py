import re

from django.db.models import Case, Count, DecimalField, F, IntegerField, Q, Sum, When
from django.db.models.functions import Now
from django.utils import timezone

from ung_dung.chung.permissions import thay_toan_chuoi
from ung_dung.danh_muc.models import Thuoc
from ung_dung.danh_muc.selectors import them_gia_va_anh

from .gio_hang import KHOA_GIO
from .models import (
    TRANG_THAI_GIU,
    ChiTietPhieuBan,
    DonHang,
    PhanBoPhieuBan,
    PhieuBan,
    YeuCauXuatHoaDon,
)


def lay_gio(phien):
    return phien.get(KHOA_GIO, {})


def lay_dong_gio(gio):
    """Các dòng giỏ kèm giá đang áp dụng; thuốc đã ngừng kinh doanh có thuoc=None."""
    cac_thuoc = (
        them_gia_va_anh(Thuoc.objects.filter(dang_hoat_dong=True))
        .select_related("don_vi_tinh")
        .in_bulk([int(ma) for ma in gio])
    )
    cac_dong = []
    for ma, so_luong in gio.items():
        thuoc = cac_thuoc.get(int(ma))
        cac_dong.append(
            {
                "id_thuoc": int(ma),
                "thuoc": thuoc,
                "so_luong": so_luong,
                "thanh_tien": thuoc.don_gia * so_luong if thuoc else 0,
            }
        )
    return cac_dong


def gio_duoc_giu(cac_dong):
    return bool(cac_dong) and all(dong["thuoc"] for dong in cac_dong)


def tom_tat_gio(cac_dong):
    hop_le = [dong for dong in cac_dong if dong["thuoc"]]
    return {
        "tien_hang": sum(dong["thanh_tien"] for dong in hop_le),
        "so_luong": sum(dong["so_luong"] for dong in hop_le),
        "co_ke_don": any(dong["thuoc"].la_thuoc_ke_don for dong in hop_le),
        "hop_le": gio_duoc_giu(cac_dong),
    }


def chuan_hoa_so_dien_thoai(chuoi):
    """'+84 912 345 678' hoặc '0912.345.678' thành '0912345678'; chuỗi khác giữ nguyên."""
    gon = re.sub(r"[\s.()-]", "", chuoi or "")
    if re.fullmatch(r"\+?84[0-9]{8,10}", gon):
        gon = "0" + gon.lstrip("+")[2:]
    return gon if re.fullmatch(r"[0-9]{3,11}", gon) else chuoi


def tim_don(tap_hop, tu_khoa):
    """Tìm đơn theo mã, tên khách, SĐT người nhận hoặc SĐT tài khoản khách.

    Đơn nhận tại quầy không có SĐT người nhận nên phải tìm cả SĐT của tài khoản khách.
    """
    so = chuan_hoa_so_dien_thoai(tu_khoa)
    return tap_hop.filter(
        Q(ma_don_hang__icontains=tu_khoa)
        | Q(khach_hang__ten_dang_nhap__icontains=tu_khoa)
        | Q(khach_hang__ho_ten__icontains=tu_khoa)
        | Q(so_dien_thoai_nhan__icontains=so)
        | Q(khach_hang__so_dien_thoai__icontains=so)
    )


def lay_don(nguoi, *, trang_thai="", hinh_thuc_nhan="", tim=""):
    tap_hop = (
        DonHang.objects.select_related("chi_nhanh", "khach_hang")
        .annotate(
            con_hieu_luc=Q(trang_thai__in=TRANG_THAI_GIU, thoi_diem_het_giu__gt=Now()),
            qua_han_giu=Q(trang_thai__in=TRANG_THAI_GIU, thoi_diem_het_giu__lte=Now()),
        )
        .order_by("-pk")
    )
    if not thay_toan_chuoi(nguoi):
        tap_hop = tap_hop.filter(
            **(
                {"khach_hang": nguoi}
                if nguoi.vai_tro == "khach_hang"
                else {"chi_nhanh_id": nguoi.chi_nhanh_id}
            )
        )
    if trang_thai:
        tap_hop = tap_hop.filter(trang_thai=trang_thai)
    if hinh_thuc_nhan:
        tap_hop = tap_hop.filter(hinh_thuc_nhan=hinh_thuc_nhan)
    if tim:
        tap_hop = tim_don(tap_hop, tim)
    return tap_hop


def don_cho_doi_soat_cod(tap_hop):
    """Đơn COD đã giao xong nhưng nhà thuốc chưa nhận tiền từ người giao."""
    return tap_hop.filter(
        cac_giao_dich__phuong_thuc="cod", cac_giao_dich__trang_thai="cho"
    ).distinct()


def don_cho_hoan_tien(tap_hop):
    return tap_hop.filter(trang_thai_thanh_toan="cho_hoan_tien")


# (giờ còn lại tối đa, mức) theo thứ tự; đơn chờ thanh toán chỉ có 30 phút nên ngưỡng ngắn hơn.
MUC_GAP = {
    "cho_thanh_toan": ((10 / 60, "gap"), (0.5, "sap_het")),
    "mac_dinh": ((1, "gap"), (6, "sap_het")),
}
HAU_QUA_QUA_HAN = {
    "dang_giu": "Quá hạn, hệ thống tự chuyển đơn sang hết hạn và nhả hàng cho khách khác.",
    "cho_thanh_toan": "Quá hạn, hệ thống tự hủy đơn và nhả hàng; tiền tới sau sẽ chờ hoàn.",
    "cho_xac_nhan": "Quá hạn, hệ thống tự hủy đơn và nhả hàng.",
}


def _doc_thoi_luong(giay):
    phut = max(int(giay // 60), 0)
    gio, phut = divmod(phut, 60)
    ngay, gio = divmod(gio, 24)
    cac_phan = [f"{ngay} ngày"] * bool(ngay) + [f"{gio} giờ"] * bool(gio)
    if not ngay:
        cac_phan.append(f"{phut} phút")
    return " ".join(cac_phan)


def thong_tin_han(don, bay_gio=None):
    """Hạn xử lý của đơn đang giữ hàng: chữ "còn 2 giờ 15 phút", mức gấp và hậu quả.

    Trả None khi đơn không còn ở trạng thái có hạn giữ.
    """
    if don.trang_thai not in TRANG_THAI_GIU:
        return None
    bay_gio = bay_gio or timezone.now()
    giay = (don.thoi_diem_het_giu - bay_gio).total_seconds()
    hau_qua = HAU_QUA_QUA_HAN.get(don.trang_thai, "")
    if don.trang_thai == "cho_xac_nhan" and don.phuong_thuc_thanh_toan != "cod":
        hau_qua = "Quá hạn, hệ thống tự hủy đơn, nhả hàng và nhà thuốc phải hoàn tiền cho khách."
    if giay <= 0:
        return {"chu": f"đã quá hạn {_doc_thoi_luong(-giay)}", "muc": "qua_han", "hau_qua": hau_qua}
    muc = "binh_thuong"
    for gio_toi_da, ten in MUC_GAP.get(don.trang_thai, MUC_GAP["mac_dinh"]):
        if giay <= gio_toi_da * 3600:
            muc = ten
            break
    return {"chu": f"còn {_doc_thoi_luong(giay)}", "muc": muc, "hau_qua": hau_qua}


def dem_don_theo_trang_thai(nguoi):
    return dict(
        lay_don(nguoi)
        .order_by()
        .values_list("trang_thai")
        .annotate(so=Count("pk"))
        .values_list("trang_thai", "so")
    )


def lay_chi_tiet_don(don):
    return don.cac_dong.select_related("thuoc__don_vi_tinh").order_by("pk")


def lay_lo_da_xuat(don):
    return (
        PhanBoPhieuBan.objects.filter(chi_tiet_phieu_ban__phieu_ban__don_hang=don)
        .select_related("chi_tiet_phieu_ban", "ton_kho__lo_thuoc")
        .order_by("pk")
    )


def lay_lich_su(don):
    return don.cac_lich_su.select_related("nguoi_thuc_hien").order_by("thoi_diem_tao", "pk")


def lay_phieu_ban(nguoi):
    tap_hop = PhieuBan.objects.select_related("chi_nhanh", "nguoi_lap", "don_hang").order_by(
        "-thoi_diem_tao", "-pk"
    )
    if not thay_toan_chuoi(nguoi):
        tap_hop = tap_hop.filter(chi_nhanh_id=nguoi.chi_nhanh_id)
    return tap_hop


def chi_tiet_ban(phieu):
    return ChiTietPhieuBan.objects.filter(phieu_ban=phieu).annotate(
        thanh_tien=F("so_luong") * F("don_gia")
    )


def tong_tien_ban(phieu):
    return (
        chi_tiet_ban(phieu).aggregate(tong=Sum("thanh_tien", output_field=DecimalField()))["tong"]
        or 0
    )


def lay_yeu_cau_xuat_hoa_don(nguoi, *, trang_thai=""):
    """Yêu cầu hóa đơn công ty trong phạm vi chi nhánh; chờ xử lý lên đầu."""
    tap_hop = YeuCauXuatHoaDon.objects.select_related(
        "don_hang__chi_nhanh", "don_hang__khach_hang", "nguoi_xu_ly"
    ).order_by(
        # Yêu cầu chờ xử lý đứng đầu, rồi mới nhất trước.
        Case(When(trang_thai="cho_xu_ly", then=0), default=1, output_field=IntegerField()),
        "-thoi_diem_tao",
    )
    if not thay_toan_chuoi(nguoi):
        tap_hop = tap_hop.filter(don_hang__chi_nhanh_id=nguoi.chi_nhanh_id)
    if trang_thai:
        tap_hop = tap_hop.filter(trang_thai=trang_thai)
    return tap_hop


def du_lieu_quay_ban(cac_chi_nhanh):
    """Dữ liệu màn bán tại quầy: thuốc, giá đang áp dụng, bao gói, tồn khả dụng theo chi nhánh.

    Chỉ để hiển thị và tính tạm trên trình duyệt; giá, tồn và FEFO vẫn do ban_tai_quay
    tính lại khi xác nhận.
    """
    from ung_dung.danh_muc.models import QuyDoiBaoGoi
    from ung_dung.kho.selectors import lay_ton_kha_dung

    cac_thuoc = (
        them_gia_va_anh(Thuoc.objects.filter(dang_hoat_dong=True))
        .select_related("don_vi_tinh")
        .order_by("ten_thuoc")
    )
    bao_goi = {}
    for qd in QuyDoiBaoGoi.objects.order_by("he_so"):
        bao_goi.setdefault(qd.thuoc_id, []).append(
            {"id": qd.pk, "ten": qd.ten_quy_doi_bao_goi, "he_so": qd.he_so}
        )
    ton = {}
    for chi_nhanh_id, thuoc_id, tong in (
        lay_ton_kha_dung()
        .filter(chi_nhanh__in=cac_chi_nhanh)
        .values_list("chi_nhanh_id", "lo_thuoc__thuoc_id")
        .annotate(tong=Sum("kha_dung"))
        .order_by()
    ):
        ton.setdefault(str(chi_nhanh_id), {})[str(thuoc_id)] = tong
    return {
        "thuoc": [
            {
                "id": t.pk,
                "ma": t.ma_thuoc,
                "ten": t.ten_thuoc,
                "hoat_chat": t.hoat_chat or "",
                "don_vi": t.don_vi_tinh.ten_don_vi_tinh,
                "don_gia": int(t.don_gia),
                "gia_goc": int(t.gia_ban),
                "ke_don": t.la_thuoc_ke_don,
                "bao_goi": bao_goi.get(t.pk, []),
            }
            for t in cac_thuoc
        ],
        "ton": ton,
    }


def lay_phieu_ban_danh_sach(nguoi):
    """Phiếu bán kèm số mặt hàng, tổng tiền hàng sau ưu đãi thành viên và cách khách trả."""
    from django.db.models import CharField, ExpressionWrapper, OuterRef, Subquery, Value

    from ung_dung.thanh_toan.models import PHUONG_THUC, GiaoDichThanhToan

    dong = ChiTietPhieuBan.objects.filter(phieu_ban=OuterRef("pk")).order_by().values("phieu_ban")
    tien = ExpressionWrapper(
        F("so_luong") * F("don_gia") - F("giam_gia_phan_bo"), output_field=DecimalField()
    )
    phuong_thuc = GiaoDichThanhToan.objects.filter(
        phieu_ban=OuterRef("pk"), loai_giao_dich="thu"
    ).values("phuong_thuc")[:1]
    return lay_phieu_ban(nguoi).annotate(
        so_mat_hang=Subquery(dong.annotate(n=Count("pk")).values("n")),
        tong_tien=Subquery(dong.annotate(t=Sum(tien)).values("t"), output_field=DecimalField()),
        ma_phuong_thuc=Subquery(phuong_thuc),
        cach_tra=Case(
            *(When(ma_phuong_thuc=ma, then=Value(nhan)) for ma, nhan in PHUONG_THUC),
            default=Value(""),
            output_field=CharField(),
        ),
    )
