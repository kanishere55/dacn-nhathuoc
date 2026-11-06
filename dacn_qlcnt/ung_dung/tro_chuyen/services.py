from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from ung_dung.chung.van_ban import cat_khoang_trang

from .models import CuocTroChuyen, TinNhan
from .permissions import kiem_tra_phong


@transaction.atomic
def mo_phong(nguoi, chi_nhanh):
    if not nguoi.is_authenticated or not nguoi.is_active or nguoi.vai_tro != "khach_hang":
        raise PermissionDenied("Chỉ khách hàng được mở cuộc trò chuyện.")
    if not chi_nhanh.dang_hoat_dong:
        raise ValidationError("Chi nhánh đã ngừng hoạt động.")
    phong, _ = CuocTroChuyen.objects.get_or_create(khach_hang=nguoi, chi_nhanh=chi_nhanh)
    return phong


@transaction.atomic
def ghi_tin_nhan(nguoi, phong, ma, noi_dung):
    kiem_tra_phong(nguoi, phong)
    try:
        ma = str(UUID(ma))
    except (ValueError, TypeError, AttributeError) as loi:
        raise ValidationError("Mã tin nhắn không hợp lệ.") from loi
    if not isinstance(noi_dung, str):
        raise ValidationError("Tin nhắn phải là văn bản.")
    noi_dung = cat_khoang_trang(noi_dung)
    if not noi_dung or len(noi_dung) > 2000 or "\x00" in noi_dung:
        raise ValidationError("Tin nhắn phải có từ 1 đến 2000 ký tự hợp lệ.")
    tin, da_tao = TinNhan.objects.get_or_create(
        nguoi_gui=nguoi,
        ma_tin_nhan=ma,
        defaults={"cuoc_tro_chuyen": phong, "noi_dung_tin_nhan": noi_dung},
    )
    if tin.cuoc_tro_chuyen_id != phong.pk or tin.noi_dung_tin_nhan != noi_dung:
        raise ValidationError("Mã đã được dùng cho tin nhắn khác.")
    return tin, da_tao
