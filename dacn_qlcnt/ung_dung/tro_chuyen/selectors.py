"""Đọc dữ liệu trò chuyện: hộp thư theo phía người xem, hàng chờ, số chưa đọc, lịch sử tải dần.

Hộp thư dựa trên cột tin_cuoi (lưu sẵn, có chỉ mục) nên vẫn nhanh khi có hàng nghìn cuộc trò
chuyện; chỉ số tin chưa đọc là subquery, chạy trên chỉ mục (phòng, id tin) của tin_nhan.
"""

from django.db.models import (
    BooleanField,
    Count,
    Exists,
    ExpressionWrapper,
    F,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
)
from django.db.models.functions import Coalesce

from ung_dung.chung.permissions import co_quyen, thay_toan_chuoi

from .models import CuocTroChuyen, TinNhan
from .permissions import kiem_tra_phong

# Các thẻ hàng chờ của hộp thư nhân sự, theo thứ tự công việc.
HANG_CHO = [
    ("cho_tra_loi", "Chờ trả lời"),
    ("da_tra_loi", "Đã trả lời"),
    ("da_xong", "Đã xong"),
    ("tat_ca", "Tất cả"),
]
LOAI_HOP_THU = [("tu_van", "Tư vấn"), ("don_hang", "Về đơn hàng")]
SO_TIN_MOI_LAN = 30

# Tin cuối do khách gửi trong phòng chưa đóng nghĩa là khách đang chờ nhà thuốc.
DIEU_KIEN_CHO = Q(trang_thai_xu_ly="dang_mo", tin_cuoi__nguoi_gui_id=F("khach_hang_id"))


def lay_cac_phong(nguoi) -> QuerySet:
    """Phòng người xem được thấy. Phòng chưa có tin (dữ liệu cũ) không bao giờ hiện."""
    cac_phong = CuocTroChuyen.objects.filter(tin_cuoi__isnull=False).select_related(
        "khach_hang", "chi_nhanh", "don_hang", "tin_cuoi"
    )
    if not nguoi.is_authenticated or not nguoi.is_active:
        return cac_phong.none()
    if nguoi.vai_tro == "khach_hang":
        return cac_phong.filter(khach_hang=nguoi)
    if co_quyen(nguoi, "tro_chuyen.dung"):
        if thay_toan_chuoi(nguoi):
            return cac_phong
        if nguoi.chi_nhanh_id:
            return cac_phong.filter(chi_nhanh_id=nguoi.chi_nhanh_id)
    return cac_phong.none()


def _la_khach(nguoi):
    return getattr(nguoi, "vai_tro", None) == "khach_hang"


def _tin_chua_doc(nguoi):
    """Điều kiện tin chưa đọc theo phía người xem, dùng trong subquery theo phòng."""
    if _la_khach(nguoi):
        # Khách: tin do nhà thuốc gửi, mới hơn mốc khách đã đọc.
        return ~Q(nguoi_gui_id=OuterRef("khach_hang_id")) & Q(
            pk__gt=Coalesce(OuterRef("tin_khach_da_doc_id"), 0)
        )
    return Q(nguoi_gui_id=OuterRef("khach_hang_id")) & Q(
        pk__gt=Coalesce(OuterRef("tin_nha_thuoc_da_doc_id"), 0)
    )


def kem_tom_tat(cac_phong, nguoi):
    chua_doc = (
        TinNhan.objects.filter(Q(cuoc_tro_chuyen_id=OuterRef("pk")) & _tin_chua_doc(nguoi))
        .order_by()
        .values("cuoc_tro_chuyen_id")
        .annotate(n=Count("pk"))
        .values("n")
    )
    return cac_phong.annotate(
        noi_dung_cuoi=F("tin_cuoi__noi_dung_tin_nhan"),
        luc_gui_cuoi=F("tin_cuoi__thoi_diem_tao"),
        nguoi_gui_cuoi=F("tin_cuoi__nguoi_gui_id"),
        id_tin_cuoi=F("tin_cuoi_id"),
        so_chua_doc=Coalesce(Subquery(chua_doc, output_field=IntegerField()), 0),
        cho_tra_loi=ExpressionWrapper(DIEU_KIEN_CHO, output_field=BooleanField()),
    )


def loc_hang_cho(cac_phong, hang_cho):
    """Lọc và sắp theo thẻ hàng chờ. Chờ trả lời: khách chờ lâu nhất lên đầu (xử lý lần lượt)."""
    if hang_cho == "cho_tra_loi":
        return cac_phong.filter(DIEU_KIEN_CHO).order_by("tin_cuoi_id")
    if hang_cho == "da_tra_loi":
        cac_phong = cac_phong.filter(trang_thai_xu_ly="dang_mo").exclude(DIEU_KIEN_CHO)
    elif hang_cho == "da_xong":
        cac_phong = cac_phong.filter(trang_thai_xu_ly="da_xong")
    return cac_phong.order_by("-tin_cuoi_id")


def tim_phong(cac_phong, tu_khoa):
    """Tìm theo tên, tên đăng nhập, số điện thoại khách, mã đơn hoặc nội dung bất kỳ tin nào."""
    if not tu_khoa:
        return cac_phong
    co_tin = TinNhan.objects.filter(
        cuoc_tro_chuyen_id=OuterRef("pk"), noi_dung_tin_nhan__icontains=tu_khoa
    )
    return cac_phong.filter(
        Q(khach_hang__ho_ten__icontains=tu_khoa)
        | Q(khach_hang__ten_dang_nhap__icontains=tu_khoa)
        | Q(khach_hang__so_dien_thoai__icontains=tu_khoa)
        | Q(don_hang__ma_don_hang__icontains=tu_khoa)
        | Exists(co_tin)
    )


def lay_hop_thu(nguoi, hang_cho="tat_ca"):
    """Hộp thư theo phía người xem kèm tóm tắt tin cuối và số chưa đọc."""
    return loc_hang_cho(kem_tom_tat(lay_cac_phong(nguoi), nguoi), hang_cho)


def dem_hang_cho(cac_phong):
    """Số phòng ở từng thẻ hàng chờ, tính trên tập đã áp bộ lọc loại / chi nhánh / tìm kiếm."""
    return cac_phong.order_by().aggregate(
        cho_tra_loi=Count("pk", filter=DIEU_KIEN_CHO),
        da_tra_loi=Count("pk", filter=Q(trang_thai_xu_ly="dang_mo") & ~DIEU_KIEN_CHO),
        da_xong=Count("pk", filter=Q(trang_thai_xu_ly="da_xong")),
        tat_ca=Count("pk"),
    )


def dem_chua_doc(nguoi):
    """Tổng tin chưa đọc của người xem trên mọi phòng mình thuộc về (cho huy hiệu)."""
    if not getattr(nguoi, "is_authenticated", False):
        return 0
    if not _la_khach(nguoi) and not co_quyen(nguoi, "tro_chuyen.dung"):
        return 0
    phong = lay_cac_phong(nguoi).order_by().values("pk")
    if _la_khach(nguoi):
        dieu_kien = ~Q(nguoi_gui_id=F("cuoc_tro_chuyen__khach_hang_id")) & Q(
            pk__gt=Coalesce(F("cuoc_tro_chuyen__tin_khach_da_doc_id"), 0)
        )
    else:
        dieu_kien = Q(nguoi_gui_id=F("cuoc_tro_chuyen__khach_hang_id")) & Q(
            pk__gt=Coalesce(F("cuoc_tro_chuyen__tin_nha_thuoc_da_doc_id"), 0)
        )
    return TinNhan.objects.filter(dieu_kien, cuoc_tro_chuyen__in=phong).count()


def lay_phong_co_tin_moi(nguoi):
    """Phòng khách đang chờ nhà thuốc trả lời (khối tóm tắt ở tổng quan nhân sự)."""
    return lay_hop_thu(nguoi, "cho_tra_loi")


def ten_hien_thi(tai_khoan):
    return tai_khoan.ho_ten or tai_khoan.ten_dang_nhap


def bieu_dien_tin(tin, khach_id):
    return {
        "id_tin_nhan": tin.pk,
        "nguoi_gui_id": tin.nguoi_gui_id,
        "la_khach": tin.nguoi_gui_id == khach_id,
        "ten_nguoi_gui": ten_hien_thi(tin.nguoi_gui),
        "noi_dung": tin.noi_dung_tin_nhan,
        "thoi_diem": tin.thoi_diem_tao.isoformat(),
    }


def lay_tin_cu(nguoi, phong, truoc=None, so_luong=SO_TIN_MOI_LAN):
    """Một trang tin (cũ → mới) có id nhỏ hơn `truoc`; `con_nua` báo còn tin cũ hơn nữa."""
    kiem_tra_phong(nguoi, phong)
    tap_hop = TinNhan.objects.filter(cuoc_tro_chuyen=phong).select_related("nguoi_gui")
    if truoc is not None:
        tap_hop = tap_hop.filter(pk__lt=truoc)
    trang = list(tap_hop.order_by("-pk")[: so_luong + 1])
    return {
        "cac_tin": [bieu_dien_tin(tin, phong.khach_hang_id) for tin in reversed(trang[:so_luong])],
        "con_nua": len(trang) > so_luong,
    }


def lay_lich_su(nguoi, phong):
    """30 tin gần nhất kèm hai mốc đã đọc để vẽ trạng thái Đã xem và vạch Tin mới."""
    trang = lay_tin_cu(nguoi, phong)
    phong.refresh_from_db(fields=["tin_khach_da_doc", "tin_nha_thuoc_da_doc"])
    return {
        **trang,
        "khach_da_doc": phong.tin_khach_da_doc_id,
        "nha_thuoc_da_doc": phong.tin_nha_thuoc_da_doc_id,
    }


def chi_nhanh_goi_y(khach):
    """Chi nhánh gợi ý cho phòng tư vấn mới: nơi khách đặt đơn gần nhất, nếu có."""
    from ung_dung.ban_hang.models import DonHang

    don = DonHang.objects.filter(khach_hang=khach).order_by("-thoi_diem_tao").first()
    return don.chi_nhanh_id if don else None
