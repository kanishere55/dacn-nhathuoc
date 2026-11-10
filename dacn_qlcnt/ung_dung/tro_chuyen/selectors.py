"""Đọc dữ liệu trò chuyện: danh sách phòng theo phía người xem, số tin chưa đọc, lịch sử tin."""

from django.db.models import (
    BooleanField,
    Case,
    Count,
    F,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from ung_dung.chung.permissions import co_quyen, thay_toan_chuoi

from .models import CuocTroChuyen, TinNhan
from .permissions import kiem_tra_phong

LOC_HOP_THU = [
    ("cho_tra_loi", "Chờ trả lời"),
    ("don_hang", "Về đơn hàng"),
    ("tu_van", "Tư vấn"),
]


def lay_cac_phong(nguoi) -> QuerySet:
    cac_phong = CuocTroChuyen.objects.select_related(
        "khach_hang", "chi_nhanh", "don_hang"
    ).order_by("-pk")
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


def _kem_tom_tat(cac_phong, nguoi):
    tin_cuoi = TinNhan.objects.filter(cuoc_tro_chuyen_id=OuterRef("pk")).order_by("-pk")
    chua_doc = (
        TinNhan.objects.filter(Q(cuoc_tro_chuyen_id=OuterRef("pk")) & _tin_chua_doc(nguoi))
        .order_by()
        .values("cuoc_tro_chuyen_id")
        .annotate(n=Count("pk"))
        .values("n")
    )
    return cac_phong.annotate(
        noi_dung_cuoi=Subquery(tin_cuoi.values("noi_dung_tin_nhan")[:1]),
        luc_gui_cuoi=Subquery(tin_cuoi.values("thoi_diem_tao")[:1]),
        nguoi_gui_cuoi=Subquery(tin_cuoi.values("nguoi_gui_id")[:1]),
        id_tin_cuoi=Subquery(tin_cuoi.values("pk")[:1]),
        so_chua_doc=Coalesce(Subquery(chua_doc, output_field=IntegerField()), 0),
    ).annotate(
        # Tin cuối do khách gửi nghĩa là khách đang chờ nhà thuốc trả lời.
        cho_tra_loi=Case(
            When(nguoi_gui_cuoi=F("khach_hang_id"), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        ),
    )


def lay_hop_thu(nguoi, loc=""):
    """Hộp thư theo phía người xem; mới nhất ở trên, phòng chưa có tin xếp cuối."""
    cac_phong = _kem_tom_tat(lay_cac_phong(nguoi), nguoi)
    if loc == "cho_tra_loi":
        cac_phong = cac_phong.filter(cho_tra_loi=True)
    elif loc in ("don_hang", "tu_van"):
        cac_phong = cac_phong.filter(loai_cuoc_tro_chuyen=loc)
    return cac_phong.order_by(F("id_tin_cuoi").desc(nulls_last=True), "-pk")


def dem_hop_thu(nguoi):
    """Số phòng theo từng bộ lọc để hiện trên các thẻ của hộp thư nhân sự."""
    cac_phong = _kem_tom_tat(lay_cac_phong(nguoi), nguoi)
    return {
        "tat_ca": cac_phong.count(),
        "cho_tra_loi": cac_phong.filter(cho_tra_loi=True).count(),
        "don_hang": cac_phong.filter(loai_cuoc_tro_chuyen="don_hang").count(),
        "tu_van": cac_phong.filter(loai_cuoc_tro_chuyen="tu_van").count(),
    }


def dem_chua_doc(nguoi):
    """Tổng tin chưa đọc của người xem trên mọi phòng mình thuộc về (cho huy hiệu)."""
    if not getattr(nguoi, "is_authenticated", False):
        return 0
    if not _la_khach(nguoi) and not co_quyen(nguoi, "tro_chuyen.dung"):
        return 0
    phong = lay_cac_phong(nguoi).order_by()
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


def lay_lich_su(nguoi, phong):
    """100 tin gần nhất kèm hai mốc đã đọc để vẽ trạng thái Đã xem và vạch Tin mới."""
    kiem_tra_phong(nguoi, phong)
    tin_nhan = (
        TinNhan.objects.filter(cuoc_tro_chuyen=phong).select_related("nguoi_gui").order_by("-pk")
    )
    phong.refresh_from_db(fields=["tin_khach_da_doc", "tin_nha_thuoc_da_doc"])
    return {
        "cac_tin": [
            bieu_dien_tin(tin, phong.khach_hang_id) for tin in reversed(list(tin_nhan[:100]))
        ],
        "khach_da_doc": phong.tin_khach_da_doc_id,
        "nha_thuoc_da_doc": phong.tin_nha_thuoc_da_doc_id,
    }


def chi_nhanh_goi_y(khach):
    """Chi nhánh gợi ý cho phòng tư vấn mới: nơi khách đặt đơn gần nhất, nếu có."""
    from ung_dung.ban_hang.models import DonHang

    don = DonHang.objects.filter(khach_hang=khach).order_by("-thoi_diem_tao").first()
    return don.chi_nhanh_id if don else None
