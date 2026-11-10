"""Yêu cầu hóa đơn đứng tên doanh nghiệp cho đơn đã hoàn thành.

Hệ thống chỉ ghi nhận thông tin người mua và kết quả xử lý. Hóa đơn điện tử có mã
của cơ quan thuế được nhân viên phát hành trên phần mềm hóa đơn của nhà thuốc,
rồi ghi ký hiệu và số hóa đơn vào đây để khách tra cứu.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_quyen_ghi_chi_nhanh, kiem_tra_vai_tro
from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import DonHang, YeuCauXuatHoaDon
from .thong_bao_don import bao_xuat_hoa_don


@transaction.atomic
def gui_yeu_cau_xuat_hoa_don(nguoi, don, thong_tin):
    kiem_tra_vai_tro(nguoi, "khach_hang")
    don = DonHang.objects.select_for_update().get(pk=don.pk)
    if don.khach_hang_id != nguoi.pk:
        raise PermissionDenied("Đơn không thuộc tài khoản của bạn.")
    if don.trang_thai != "hoan_thanh":
        raise ValidationError("Chỉ yêu cầu hóa đơn công ty cho đơn đã hoàn thành.")
    if YeuCauXuatHoaDon.objects.filter(don_hang=don).exists():
        raise ValidationError("Đơn này đã có yêu cầu xuất hóa đơn.")
    yeu_cau = YeuCauXuatHoaDon(
        don_hang=don,
        ten_cong_ty=cat_khoang_trang(thong_tin["ten_cong_ty"]),
        ma_so_thue=cat_khoang_trang(thong_tin["ma_so_thue"]),
        dia_chi_cong_ty=cat_khoang_trang(thong_tin["dia_chi_cong_ty"]),
        email_nhan_hoa_don=cat_khoang_trang(thong_tin["email_nhan_hoa_don"]).lower(),
    )
    yeu_cau.full_clean()
    yeu_cau.save()
    return yeu_cau


@transaction.atomic
def xu_ly_yeu_cau_xuat_hoa_don(nguoi, yeu_cau, trang_thai, ghi_chu):
    yeu_cau = (
        YeuCauXuatHoaDon.objects.select_for_update()
        .select_related("don_hang__chi_nhanh", "don_hang__khach_hang")
        .get(pk=yeu_cau.pk)
    )
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, yeu_cau.don_hang.chi_nhanh, "hoa_don_cong_ty.xu_ly")
    if yeu_cau.trang_thai != "cho_xu_ly":
        raise ValidationError("Yêu cầu này đã được xử lý.")
    if trang_thai not in ("da_xuat", "tu_choi"):
        raise ValidationError("Kết quả xử lý không hợp lệ.")
    ghi_chu = cat_khoang_trang(ghi_chu)
    if not ghi_chu:
        raise ValidationError("Ghi ký hiệu và số hóa đơn đã phát hành, hoặc lý do từ chối.")
    yeu_cau.trang_thai = trang_thai
    yeu_cau.ghi_chu_xu_ly = ghi_chu
    yeu_cau.nguoi_xu_ly = nguoi
    yeu_cau.thoi_diem_xu_ly = timezone.now()
    yeu_cau.save(update_fields=["trang_thai", "ghi_chu_xu_ly", "nguoi_xu_ly", "thoi_diem_xu_ly"])
    bao_xuat_hoa_don(yeu_cau)
    return yeu_cau
