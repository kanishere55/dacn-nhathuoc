"""Giữ hàng cho đơn: mốc hạn dùng của lô, phân bổ lại phần giữ khi lô không còn dùng được.

Q03 hứa đơn giữ được đủ hàng tới hết hạn giữ; Q04 giữ theo lô. Vì vậy:
- lúc đặt chỉ giữ trên lô còn hạn tới ngày hết giữ;
- lô bị khóa bán hoặc hết hạn khi đơn còn giữ thì phần giữ được dời sang lô hợp lệ khác
  theo FEFO, cùng thứ tự khóa kho → đơn như lúc đặt hàng.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ung_dung.kho.selectors import luong_ban_duoc
from ung_dung.kho.services.giao_dich import khoa_kho, phan_bo_fefo

from ..models import TRANG_THAI_GIU, DonHang, PhanBoDonHang


def han_lo_can_cho_don(don, het_giu=None):
    """Ngày lô giữ cho đơn phải còn hạn tới: ngày hết giữ của đơn."""
    return timezone.localdate(het_giu or don.thoi_diem_het_giu)


def _lo_dung_duoc(ton_kho, con_han_den):
    lo = ton_kho.lo_thuoc
    return (
        lo.duoc_phep_ban
        and lo.ngay_het_han >= max(timezone.localdate(), con_han_den)
        and lo.thuoc.dang_hoat_dong
        and ton_kho.chi_nhanh.dang_hoat_dong
    )


def phan_bo_lai_don(don, *, con_han_den=None):
    """Dời phần giữ của các dòng đang nằm trên lô không đạt mốc sang lô khác theo FEFO.

    Gọi trong transaction đã khóa kho chi nhánh và đơn. Không đủ hàng thì ném
    ValidationError nêu rõ thuốc thiếu; người gọi quyết định giữ nguyên hay báo lỗi.
    Trả số dòng đã phân bổ lại.
    """
    con_han_den = con_han_den or han_lo_can_cho_don(don)
    so_dong = 0
    for dong in don.cac_dong.select_related("thuoc__don_vi_tinh").order_by("pk"):
        cac_phan_bo = list(
            PhanBoDonHang.objects.filter(chi_tiet_don_hang=dong).select_related(
                "ton_kho__lo_thuoc__thuoc", "ton_kho__chi_nhanh"
            )
        )
        if sum(pb.so_luong for pb in cac_phan_bo) == dong.so_luong and all(
            _lo_dung_duoc(pb.ton_kho, con_han_den) for pb in cac_phan_bo
        ):
            continue
        PhanBoDonHang.objects.filter(chi_tiet_don_hang=dong).delete()
        for ton, lay in phan_bo_fefo(
            don.chi_nhanh, dong.thuoc, dong.so_luong, bo_qua_don=don, con_han_den=con_han_den
        ):
            PhanBoDonHang.objects.create(chi_tiet_don_hang=dong, ton_kho=ton, so_luong=lay)
        so_dong += 1
    return so_dong


def _dieu_kien_giu_hieu_luc():
    return Q(
        chi_tiet_don_hang__don_hang__trang_thai__in=TRANG_THAI_GIU,
        chi_tiet_don_hang__don_hang__thoi_diem_het_giu__gt=timezone.now(),
    )


def don_giu_tren_lo_hong(chi_nhanh=None, lo_thuoc=None):
    """Đơn còn hiệu lực có phần giữ nằm trên lô đã hết hạn hoặc đang khóa bán."""
    tap_hop = PhanBoDonHang.objects.filter(_dieu_kien_giu_hieu_luc())
    if lo_thuoc is not None:
        tap_hop = tap_hop.filter(ton_kho__lo_thuoc=lo_thuoc)
    else:
        tap_hop = tap_hop.filter(
            Q(ton_kho__lo_thuoc__ngay_het_han__lt=timezone.localdate())
            | Q(ton_kho__lo_thuoc__duoc_phep_ban=False)
        )
    if chi_nhanh is not None:
        tap_hop = tap_hop.filter(ton_kho__chi_nhanh=chi_nhanh)
    return DonHang.objects.filter(pk__in=tap_hop.values("chi_tiet_don_hang__don_hang")).order_by(
        "pk"
    )


def phan_bo_lai_giu(chi_nhanh, lo_thuoc=None):
    """Phân bổ lại mọi đơn của chi nhánh đang giữ trên lô hỏng (hoặc trên `lo_thuoc`).

    Gọi trong transaction; hàm tự khóa kho chi nhánh trước rồi khóa từng đơn. Trả danh
    sách (đơn, lời báo) của các đơn không đủ hàng để dời, giữ nguyên phần giữ cũ của đơn đó.
    """
    khoa_kho(chi_nhanh, cho_phep_ngung=True)
    khong_du = []
    for don in don_giu_tren_lo_hong(chi_nhanh=chi_nhanh, lo_thuoc=lo_thuoc):
        don = DonHang.objects.select_for_update().get(pk=don.pk)
        if don.trang_thai not in TRANG_THAI_GIU or don.thoi_diem_het_giu <= timezone.now():
            continue
        try:
            with transaction.atomic():
                phan_bo_lai_don(don)
        except ValidationError as loi:
            khong_du.append((don, " ".join(loi.messages)))
    return khong_du


@transaction.atomic
def phan_bo_lai_giu_cua_lo(lo_thuoc):
    """Dùng sau khi khóa bán một lô: dời phần giữ của các đơn trên lô đó ở mọi chi nhánh.

    Trả danh sách (đơn, lời báo) chưa dời được để người khóa lô liên hệ khách.
    """
    from ung_dung.kho.models import TonKho

    khong_du = []
    cac_chi_nhanh = (
        TonKho.objects.filter(lo_thuoc=lo_thuoc)
        .select_related("chi_nhanh")
        .order_by("chi_nhanh_id")
    )
    for ton in cac_chi_nhanh:
        khong_du.extend(phan_bo_lai_giu(ton.chi_nhanh, lo_thuoc=lo_thuoc))
    return khong_du


def phan_bo_lai_moi_chi_nhanh():
    """Chạy định kỳ: dời phần giữ khỏi lô vừa hết hạn hoặc bị khóa ở mọi chi nhánh."""
    from ung_dung.danh_muc.models import ChiNhanh

    cac_ma = (
        PhanBoDonHang.objects.filter(_dieu_kien_giu_hieu_luc())
        .filter(
            Q(ton_kho__lo_thuoc__ngay_het_han__lt=timezone.localdate())
            | Q(ton_kho__lo_thuoc__duoc_phep_ban=False)
        )
        .values_list("ton_kho__chi_nhanh_id", flat=True)
        .distinct()
    )
    khong_du = []
    for chi_nhanh in ChiNhanh.objects.filter(pk__in=list(cac_ma)).order_by("pk"):
        with transaction.atomic():
            khong_du.extend(phan_bo_lai_giu(chi_nhanh))
    return khong_du


def kha_nang_dap_ung(don):
    """Cảnh báo cho trang xử lý đơn: dòng nào đang giữ trên lô hỏng và còn thiếu bao nhiêu.

    Trả [] khi đơn không còn giữ hàng hoặc mọi dòng vẫn đủ. Mỗi phần tử: {thuoc, can,
    con_ban_duoc, cac_lo_hong: [(mã lô, lý do)]}.
    """
    if don.trang_thai not in TRANG_THAI_GIU or don.thoi_diem_het_giu <= timezone.now():
        return []
    con_han_den = han_lo_can_cho_don(don)
    hom_nay = timezone.localdate()
    ket_qua = []
    for dong in don.cac_dong.select_related("thuoc__don_vi_tinh").order_by("pk"):
        cac_lo_hong = []
        for pb in PhanBoDonHang.objects.filter(chi_tiet_don_hang=dong).select_related(
            "ton_kho__lo_thuoc__thuoc", "ton_kho__chi_nhanh"
        ):
            lo = pb.ton_kho.lo_thuoc
            if not lo.duoc_phep_ban:
                cac_lo_hong.append((lo.ma_lo_thuoc, "đang khóa bán"))
            elif lo.ngay_het_han < hom_nay:
                cac_lo_hong.append((lo.ma_lo_thuoc, f"hết hạn {lo.ngay_het_han:%d/%m/%Y}"))
            elif not _lo_dung_duoc(pb.ton_kho, con_han_den):
                cac_lo_hong.append((lo.ma_lo_thuoc, f"hạn {lo.ngay_het_han:%d/%m/%Y} quá gần"))
        if not cac_lo_hong:
            continue
        con_ban_duoc = luong_ban_duoc(
            [don.chi_nhanh], [dong.thuoc_id], con_han_den=con_han_den, bo_qua_don=don
        ).get((don.chi_nhanh_id, dong.thuoc_id), 0)
        ket_qua.append(
            {
                "thuoc": dong.thuoc,
                "can": dong.so_luong,
                "con_ban_duoc": con_ban_duoc,
                "du": con_ban_duoc >= dong.so_luong,
                "cac_lo_hong": cac_lo_hong,
            }
        )
    return ket_qua
