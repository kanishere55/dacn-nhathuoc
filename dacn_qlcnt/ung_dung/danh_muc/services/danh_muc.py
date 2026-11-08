import re

from django.core.exceptions import ValidationError
from django.db import transaction

from ung_dung.chung.permissions import kiem_tra_vai_tro
from ung_dung.chung.ten_csdl import MA_NGHIEP_VU
from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import KhuyenMai, QuyDoiBaoGoi, Thuoc
from ..selectors import DANH_MUC


@transaction.atomic
def luu_danh_muc(nguoi, loai, du_lieu, doi_tuong=None):
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
    model = DANH_MUC[loai][0]
    if doi_tuong:
        doi_tuong = model.objects.select_for_update().get(pk=doi_tuong.pk)
    else:
        doi_tuong = model()
    don_vi_cu = doi_tuong.don_vi_tinh_id if isinstance(doi_tuong, Thuoc) else None
    for ten, gia_tri in du_lieu.items():
        if ten not in {cot.name for cot in model._meta.fields if not cot.primary_key}:
            continue
        if isinstance(gia_tri, str):
            gia_tri = cat_khoang_trang(gia_tri)
            if ten.startswith("ma_") and not re.fullmatch(MA_NGHIEP_VU, gia_tri):
                raise ValidationError("Mã gồm tối đa 32 chữ hoa, số, gạch ngang hoặc gạch dưới.")
        setattr(doi_tuong, ten, gia_tri)
    if don_vi_cu and doi_tuong.don_vi_tinh_id != don_vi_cu:
        raise ValidationError(
            "Đơn vị cơ sở của thuốc đã tạo được giữ cố định để bảo toàn số liệu kho."
        )
    if isinstance(doi_tuong, QuyDoiBaoGoi) and doi_tuong.pk:
        cu = model.objects.get(pk=doi_tuong.pk)
        if cu.thuoc_id != doi_tuong.thuoc_id or cu.he_so != doi_tuong.he_so:
            raise ValidationError("Không đổi thuốc/hệ số của quy đổi đã tạo; hãy tạo bao gói mới.")
    if loai == "nhan_vien" and doi_tuong.tai_khoan.vai_tro not in {
        "nhan_vien",
        "quan_ly_chi_nhanh",
    }:
        raise ValidationError(
            "Hồ sơ nhân viên phải liên kết tài khoản nhân viên hoặc quản lý chi nhánh."
        )
    if isinstance(doi_tuong, KhuyenMai):
        kiem_khuyen_mai_trung(doi_tuong)
    doi_tuong.full_clean()
    doi_tuong.save()
    return doi_tuong


def kiem_khuyen_mai_trung(khuyen_mai):
    """Một thuốc chỉ có một đợt giảm giá đang hoạt động trong cùng một ngày.

    Khóa dòng thuốc để hai quản trị lưu cùng lúc không tạo được hai đợt trùng.
    """
    if not khuyen_mai.dang_hoat_dong:
        return
    Thuoc.objects.select_for_update().get(pk=khuyen_mai.thuoc_id)
    trung = (
        KhuyenMai.objects.filter(
            thuoc_id=khuyen_mai.thuoc_id,
            dang_hoat_dong=True,
            ngay_bat_dau__lte=khuyen_mai.ngay_ket_thuc,
            ngay_ket_thuc__gte=khuyen_mai.ngay_bat_dau,
        )
        .exclude(pk=khuyen_mai.pk)
        .first()
    )
    if trung:
        raise ValidationError(
            f"Thuốc đã có đợt {trung.ma_khuyen_mai} từ {trung.ngay_bat_dau:%d/%m/%Y} "
            f"đến {trung.ngay_ket_thuc:%d/%m/%Y}. Hãy dừng đợt đó hoặc chọn ngày khác."
        )
