"""Xử lý đơn đặt giữ sau khi đặt: hủy và tự chuyển hết hạn khi quá thời gian giữ.

Khách nhận hàng và trả tiền tại quầy được ghi bằng phiếu bán (services/phieu_ban.py).
"""

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_quyen_ghi_chi_nhanh, kiem_tra_vai_tro
from ung_dung.kho.services.giao_dich import khoa_kho

from ..models import DonHang
from .giu_hang import phan_bo_lai_moi_chi_nhanh
from .thong_bao_don import bao_doi_trang_thai
from .trang_thai import doi_trang_thai


def _khoa_don(don, nguoi, quyen="don_hang.xu_ly"):
    """Kiểm quyền rồi khóa kho chi nhánh trước, đơn sau, cùng thứ tự với đặt giữ."""
    if nguoi is not None:
        if nguoi.vai_tro == "khach_hang":
            kiem_tra_vai_tro(nguoi, "khach_hang")
            if don.khach_hang_id != nguoi.pk:
                raise PermissionDenied("Đơn không thuộc tài khoản của bạn.")
        else:
            kiem_tra_quyen_ghi_chi_nhanh(nguoi, don.chi_nhanh, quyen)
    khoa_kho(don.chi_nhanh, cho_phep_ngung=True)
    return (
        DonHang.objects.select_for_update(of=("self",)).select_related("khach_hang").get(pk=don.pk)
    )


@transaction.atomic
def huy_don(nguoi, don, ly_do=""):
    """Khách hoặc nhà thuốc hủy đơn đang giữ; lượng giữ được giải phóng theo trạng thái.

    Đơn đã quá hạn giữ mà lệnh định kỳ chưa kịp chạy thì ghi là hết hạn, đúng sự thật.
    """
    don = _khoa_don(don, nguoi)
    if don.trang_thai == "dang_giu" and don.thoi_diem_het_giu <= timezone.now():
        doi_trang_thai(don, "het_han", nguoi, "Đơn đã quá hạn giữ khi hủy")
    else:
        ghi_chu = ly_do or (
            "Khách hủy đơn" if nguoi.vai_tro == "khach_hang" else "Nhà thuốc hủy đơn"
        )
        doi_trang_thai(don, "da_huy", nguoi, ghi_chu)
    bao_doi_trang_thai(don, ly_do)
    return don


QUA_HAN = {"dang_giu": ("het_han", "Quá 24 giờ chưa nhận tại quầy")}


def xu_ly_qua_han():
    """Đổi trạng thái các đơn đã quá hạn giữ; chạy định kỳ bằng lệnh quản lý.

    Kèm theo: dời phần giữ của đơn còn hiệu lực khỏi lô vừa hết hạn hoặc bị khóa bán.
    """
    phan_bo_lai_moi_chi_nhanh()
    so_don = 0
    for ma in DonHang.objects.filter(
        trang_thai__in=QUA_HAN, thoi_diem_het_giu__lte=timezone.now()
    ).values_list("pk", flat=True):
        with transaction.atomic():
            don = _khoa_don(DonHang.objects.select_related("chi_nhanh").get(pk=ma), None)
            if don.trang_thai not in QUA_HAN or don.thoi_diem_het_giu > timezone.now():
                continue
            den, ghi_chu = QUA_HAN[don.trang_thai]
            doi_trang_thai(don, den, None, ghi_chu)
            bao_doi_trang_thai(don, ghi_chu)
            so_don += 1
    return so_don
