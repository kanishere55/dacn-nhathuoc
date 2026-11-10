"""Nghiệp vụ trò chuyện: mở phòng tư vấn / phòng về đơn hàng, ghi tin, đánh dấu đã đọc."""

from uuid import UUID, uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from ung_dung.chung.van_ban import cat_khoang_trang

from .models import CuocTroChuyen, TinNhan
from .permissions import duoc_phu_trach_chi_nhanh, kiem_tra_phong


def _la_khach(nguoi):
    return nguoi.is_authenticated and nguoi.is_active and nguoi.vai_tro == "khach_hang"


def _lay_hoac_tao(**khoa):
    # Hai yêu cầu mở cùng phòng cùng lúc: bản tạo sau vướng ràng buộc duy nhất thì đọc lại.
    try:
        with transaction.atomic():
            return CuocTroChuyen.objects.get_or_create(**khoa)[0]
    except IntegrityError:
        return CuocTroChuyen.objects.get(
            khach_hang_id=khoa["khach_hang_id"],
            chi_nhanh_id=khoa["chi_nhanh_id"],
            don_hang=khoa["don_hang"],
        )


def mo_phong(nguoi, chi_nhanh):
    """Phòng tư vấn chung của khách với một chi nhánh, không cần đã mua hàng."""
    if not _la_khach(nguoi):
        raise PermissionDenied("Chỉ khách hàng được mở cuộc trò chuyện tư vấn.")
    if not chi_nhanh.dang_hoat_dong:
        raise ValidationError("Chi nhánh đã ngừng hoạt động.")
    return _lay_hoac_tao(
        khach_hang_id=nguoi.pk,
        chi_nhanh_id=chi_nhanh.pk,
        don_hang=None,
        loai_cuoc_tro_chuyen="tu_van",
    )


def mo_phong_don_hang(nguoi, don):
    """Phòng về một đơn: khách mở từ đơn của mình, nhân sự mở để liên hệ khách về đơn."""
    if _la_khach(nguoi):
        if don.khach_hang_id != nguoi.pk:
            raise PermissionDenied("Đơn không thuộc tài khoản của bạn.")
    elif not duoc_phu_trach_chi_nhanh(nguoi, don.chi_nhanh_id):
        raise PermissionDenied("Bạn không phụ trách chi nhánh của đơn này.")
    return _lay_hoac_tao(
        khach_hang_id=don.khach_hang_id,
        chi_nhanh_id=don.chi_nhanh_id,
        don_hang=don,
        loai_cuoc_tro_chuyen="don_hang",
    )


def ben_cua(nguoi, phong):
    return "khach" if nguoi.pk == phong.khach_hang_id else "nha_thuoc"


def _day_moc_da_doc(phong, ben, tin_id):
    """Chỉ cho mốc đã đọc tiến lên; trả về True khi mốc thực sự thay đổi."""
    cot = "tin_khach_da_doc" if ben == "khach" else "tin_nha_thuoc_da_doc"
    hien_tai = getattr(phong, f"{cot}_id")
    if hien_tai is not None and hien_tai >= tin_id:
        return False
    setattr(phong, f"{cot}_id", tin_id)
    phong.save(update_fields=[cot])
    return True


@transaction.atomic
def danh_dau_da_doc(nguoi, phong, id_tin):
    """Người xem đã thấy tới tin `id_tin`. Trả về (bên, id) khi mốc đổi, None khi không đổi."""
    kiem_tra_phong(nguoi, phong)
    if isinstance(id_tin, bool) or not isinstance(id_tin, int):
        raise ValidationError("Mã tin không hợp lệ.")
    phong = CuocTroChuyen.objects.select_for_update().get(pk=phong.pk)
    if not TinNhan.objects.filter(pk=id_tin, cuoc_tro_chuyen=phong).exists():
        raise ValidationError("Tin không thuộc cuộc trò chuyện này.")
    ben = ben_cua(nguoi, phong)
    return (ben, id_tin) if _day_moc_da_doc(phong, ben, id_tin) else None


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
    if da_tao:
        # Người vừa trả lời chắc chắn đã xem mọi tin trước đó của phòng.
        khoa = CuocTroChuyen.objects.select_for_update().get(pk=phong.pk)
        _day_moc_da_doc(khoa, ben_cua(nguoi, khoa), tin.pk)
    return tin, da_tao


@transaction.atomic
def gui_tin_dau(nguoi, phong, noi_dung):
    """Tin đầu tiên gõ ngay ở form mở phòng (không qua WebSocket); vẫn báo nhà thuốc tức thời."""
    from .phat_tin_hieu import phat_sau_khi_luu

    tin, da_tao = ghi_tin_nhan(nguoi, phong, str(uuid4()), noi_dung)
    if da_tao:
        phat_sau_khi_luu(nguoi, phong, tin)
    return tin
