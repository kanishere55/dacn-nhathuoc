"""Đọc dữ liệu trò chuyện: hộp thư theo phía người xem, hàng chờ, số chưa đọc, lịch sử tải dần
kèm thẻ sản phẩm / đơn hàng và ảnh của từng tin.

Hộp thư dựa trên cột tin_cuoi (lưu sẵn, có chỉ mục) nên vẫn nhanh khi có hàng nghìn cuộc trò
chuyện; chỉ số tin chưa đọc là subquery, chạy trên chỉ mục (cuộc trò chuyện, id tin) của tin_nhan.
"""

from django.db.models import (
    BooleanField,
    Count,
    Exists,
    ExpressionWrapper,
    F,
    IntegerField,
    Max,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
)
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone

from ung_dung.chung.permissions import co_quyen, thay_toan_chuoi
from ung_dung.chung.templatetags.dinh_dang import tien

from .models import AnhTinNhan, CuocTroChuyen, TinNhan
from .permissions import kiem_tra_phong

# Các thẻ hàng chờ của hộp thư nhân sự, theo thứ tự công việc.
HANG_CHO = [
    ("cho_tra_loi", "Chờ trả lời"),
    ("da_tra_loi", "Đã trả lời"),
    ("da_xong", "Đã xong"),
    ("tat_ca", "Tất cả"),
]
SO_TIN_MOI_LAN = 30

# Tin cuối do khách gửi trong cuộc chưa đóng nghĩa là khách đang chờ nhà thuốc.
DIEU_KIEN_CHO = Q(trang_thai_xu_ly="dang_mo", tin_cuoi__nguoi_gui_id=F("khach_hang_id"))


def lay_cac_phong(nguoi) -> QuerySet:
    """Cuộc trò chuyện người xem được thấy. Cuộc chưa có tin (dữ liệu cũ) không bao giờ hiện."""
    cac_phong = CuocTroChuyen.objects.filter(tin_cuoi__isnull=False).select_related(
        "khach_hang", "chi_nhanh", "tin_cuoi"
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
    """Điều kiện tin chưa đọc theo phía người xem, dùng trong subquery theo cuộc trò chuyện."""
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
        so_anh_cuoi=F("tin_cuoi__so_anh"),
        don_cuoi=F("tin_cuoi__don_hang__ma_don_hang"),
        thuoc_cuoi=F("tin_cuoi__thuoc__ten_thuoc"),
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
    """Tìm theo tên, tên đăng nhập, số điện thoại khách, nội dung tin, mã đơn hoặc tên thuốc
    khách đã hỏi trong cuộc trò chuyện."""
    if not tu_khoa:
        return cac_phong
    co_tin = TinNhan.objects.filter(cuoc_tro_chuyen_id=OuterRef("pk")).filter(
        Q(noi_dung_tin_nhan__icontains=tu_khoa)
        | Q(don_hang__ma_don_hang__icontains=tu_khoa)
        | Q(thuoc__ten_thuoc__icontains=tu_khoa)
    )
    return cac_phong.filter(
        Q(khach_hang__ho_ten__icontains=tu_khoa)
        | Q(khach_hang__ten_dang_nhap__icontains=tu_khoa)
        | Q(khach_hang__so_dien_thoai__icontains=tu_khoa)
        | Exists(co_tin)
    )


def lay_hop_thu(nguoi, hang_cho="tat_ca"):
    """Hộp thư theo phía người xem kèm tóm tắt tin cuối và số chưa đọc."""
    return loc_hang_cho(kem_tom_tat(lay_cac_phong(nguoi), nguoi), hang_cho)


def dem_hang_cho(cac_phong):
    """Số cuộc ở từng thẻ hàng chờ, tính trên tập đã áp bộ lọc chi nhánh / tìm kiếm."""
    return cac_phong.order_by().aggregate(
        cho_tra_loi=Count("pk", filter=DIEU_KIEN_CHO),
        da_tra_loi=Count("pk", filter=Q(trang_thai_xu_ly="dang_mo") & ~DIEU_KIEN_CHO),
        da_xong=Count("pk", filter=Q(trang_thai_xu_ly="da_xong")),
        tat_ca=Count("pk"),
    )


def dem_chua_doc(nguoi):
    """Tổng tin chưa đọc của người xem trên mọi cuộc mình thuộc về (cho huy hiệu)."""
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
    """Cuộc khách đang chờ nhà thuốc trả lời (khối tóm tắt ở tổng quan nhân sự)."""
    return lay_hop_thu(nguoi, "cho_tra_loi")


def ten_hien_thi(tai_khoan):
    return tai_khoan.ho_ten or tai_khoan.ten_dang_nhap


def xem_truoc(*, noi_dung, so_anh, ma_don=None, ten_thuoc=None):
    """Một dòng tóm tắt tin cho hộp thư và thông báo: chữ, hoặc "Đã gửi n ảnh"."""
    if noi_dung:
        return noi_dung
    if so_anh:
        return "Đã gửi ảnh" if so_anh == 1 else f"Đã gửi {so_anh} ảnh"
    if ma_don:
        return f"Hỏi về đơn {ma_don}"
    return f"Hỏi về {ten_thuoc}" if ten_thuoc else ""


def _cac_the_thuoc(cac_id):
    from ung_dung.danh_muc.models import Thuoc
    from ung_dung.danh_muc.selectors import them_gia_va_anh

    if not cac_id:
        return {}
    cac_thuoc = them_gia_va_anh(Thuoc.objects.filter(pk__in=cac_id).select_related("don_vi_tinh"))
    ket_qua = {}
    for thuoc in cac_thuoc:
        url = reverse("danh_muc:khach_thuoc_chi_tiet", args=[thuoc.ma_thuoc])
        ket_qua[thuoc.pk] = {
            "loai": "thuoc",
            "tieu_de": "Đang hỏi về sản phẩm",
            "ten": thuoc.ten_thuoc,
            "phu": f"{tien(thuoc.don_gia)} / {thuoc.don_vi_tinh.ten_don_vi_tinh.lower()}",
            "ke_don": thuoc.la_thuoc_ke_don,
            "url_anh": (
                reverse("danh_muc:anh_thuoc", args=[thuoc.id_anh_dai_dien])
                if thuoc.id_anh_dai_dien
                else ""
            ),
            "url_khach": url,
            "url_nha_thuoc": url,
        }
    return ket_qua


def the_thuoc(thuoc):
    """Thẻ "Bạn đang hỏi về sản phẩm này" của một thuốc."""
    return _cac_the_thuoc([thuoc.pk]).get(thuoc.pk)


def the_don(don):
    """Thẻ "Bạn đang hỏi về đơn hàng này" của một đơn."""
    return {
        "loai": "don",
        "tieu_de": "Đang hỏi về đơn hàng",
        "ten": f"Đơn {don.ma_don_hang}",
        "phu": (
            f"{don.get_trang_thai_display()} · {tien(don.tong_thanh_toan)} · "
            f"{timezone.localtime(don.thoi_diem_tao):%d/%m/%Y}"
        ),
        "ke_don": False,
        "url_anh": "",
        "url_khach": reverse("ban_hang:khach_don_hang_chi_tiet", args=[don.pk]),
        "url_nha_thuoc": reverse("ban_hang:don_hang_chi_tiet", args=[don.pk]),
    }


def bieu_dien_cac_tin(cac_tin, khach_id):
    """Dữ liệu JSON của các tin; thẻ và ảnh nạp bằng số truy vấn cố định (không N+1)."""
    cac_tin = list(cac_tin)
    the_thuoc_theo_id = _cac_the_thuoc({tin.thuoc_id for tin in cac_tin if tin.thuoc_id})
    co_anh = [tin.pk for tin in cac_tin if tin.so_anh]
    anh_theo_tin = {}
    if co_anh:
        for anh in (
            AnhTinNhan.objects.filter(tin_nhan_id__in=co_anh)
            .only("pk", "tin_nhan_id", "chieu_rong", "chieu_cao", "thu_tu")
            .order_by("tin_nhan_id", "thu_tu")
        ):
            anh_theo_tin.setdefault(anh.tin_nhan_id, []).append(
                {"id": anh.pk, "rong": anh.chieu_rong, "cao": anh.chieu_cao}
            )
    ket_qua = []
    for tin in cac_tin:
        if tin.thuoc_id:
            the = the_thuoc_theo_id.get(tin.thuoc_id)
        elif tin.don_hang_id:
            the = the_don(tin.don_hang)
        else:
            the = None
        ket_qua.append(
            {
                "id_tin_nhan": tin.pk,
                "nguoi_gui_id": tin.nguoi_gui_id,
                "la_khach": tin.nguoi_gui_id == khach_id,
                "ten_nguoi_gui": ten_hien_thi(tin.nguoi_gui),
                "noi_dung": tin.noi_dung_tin_nhan,
                "thoi_diem": tin.thoi_diem_tao.isoformat(),
                "anh": anh_theo_tin.get(tin.pk, []),
                "the": the,
            }
        )
    return ket_qua


def bieu_dien_tin(tin, khach_id):
    return bieu_dien_cac_tin([tin], khach_id)[0]


def lay_tin_cu(nguoi, phong, truoc=None, so_luong=SO_TIN_MOI_LAN):
    """Một trang tin (cũ → mới) có id nhỏ hơn `truoc`; `con_nua` báo còn tin cũ hơn nữa."""
    kiem_tra_phong(nguoi, phong)
    tap_hop = TinNhan.objects.filter(cuoc_tro_chuyen=phong).select_related("nguoi_gui", "don_hang")
    if truoc is not None:
        tap_hop = tap_hop.filter(pk__lt=truoc)
    trang = list(tap_hop.order_by("-pk")[: so_luong + 1])
    return {
        "cac_tin": bieu_dien_cac_tin(reversed(trang[:so_luong]), phong.khach_hang_id),
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
    """Chi nhánh gợi ý khi khách hỏi mới: nơi vừa trò chuyện gần nhất, không có thì nơi đặt đơn
    gần nhất."""
    from ung_dung.ban_hang.models import DonHang

    phong = lay_cac_phong(khach).order_by("-tin_cuoi_id").first()
    if phong is not None:
        return phong.chi_nhanh_id
    don = DonHang.objects.filter(khach_hang=khach).order_by("-thoi_diem_tao").first()
    return don.chi_nhanh_id if don else None


def phong_cua_don(nguoi, don):
    """Cuộc trò chuyện chứa câu hỏi về đơn: cuộc chung của chủ đơn với chi nhánh của đơn."""
    return (
        kem_tom_tat(lay_cac_phong(nguoi), nguoi)
        .filter(khach_hang_id=don.khach_hang_id, chi_nhanh_id=don.chi_nhanh_id)
        .first()
    )


def cac_don_da_hoi(phong, so_luong=5):
    """Các đơn đã được nhắc trong cuộc trò chuyện, đơn được hỏi gần nhất trước."""
    from ung_dung.ban_hang.models import DonHang

    return (
        DonHang.objects.filter(cac_tin_nhan__cuoc_tro_chuyen=phong)
        .annotate(lan_hoi_cuoi=Max("cac_tin_nhan__id_tin_nhan"))
        .order_by("-lan_hoi_cuoi")[:so_luong]
    )


def anh_xem_duoc(nguoi):
    """Ảnh tin nhắn người xem được mở: ảnh thuộc cuộc trò chuyện người đó thấy."""
    return AnhTinNhan.objects.filter(
        tin_nhan__cuoc_tro_chuyen__in=lay_cac_phong(nguoi).values("pk")
    )
