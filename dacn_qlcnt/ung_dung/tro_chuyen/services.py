"""Nghiệp vụ trò chuyện: bắt đầu cuộc trò chuyện bằng tin đầu tiên, ghi tin, đã đọc, đã xong.

Phòng chỉ được tạo cùng tin đầu tiên trong một giao dịch: bấm "Nhắn nhà thuốc" mà chưa gửi gì
thì không có phòng nào ở cả hai phía. Khách bị giới hạn tốc độ gửi để chống spam hộp thư.
"""

from datetime import timedelta
from uuid import UUID, uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ung_dung.chung.van_ban import cat_khoang_trang

from .models import CuocTroChuyen, TinNhan
from .permissions import duoc_phu_trach_chi_nhanh, kiem_tra_phong

# Khách gửi quá số tin này trong một phút thì phải chờ; đủ cho người gõ thật, chặn gửi dồn.
GIOI_HAN_TIN_MOT_PHUT = 8
# Một khách mở tối đa từng này cuộc trò chuyện mới mỗi ngày (tư vấn + về đơn).
GIOI_HAN_PHONG_MOT_NGAY = 10


def _la_khach(nguoi):
    return nguoi.is_authenticated and nguoi.is_active and nguoi.vai_tro == "khach_hang"


def _lay_hoac_tao(**khoa):
    """Trả (phòng, mới tạo). Hai yêu cầu cùng lúc: bản sau vướng ràng buộc duy nhất thì đọc lại."""
    try:
        with transaction.atomic():
            return CuocTroChuyen.objects.get_or_create(**khoa)
    except IntegrityError:
        phong = CuocTroChuyen.objects.get(
            khach_hang_id=khoa["khach_hang_id"],
            chi_nhanh_id=khoa["chi_nhanh_id"],
            don_hang=khoa["don_hang"],
        )
        return phong, False


def _mo_phong_tu_van(nguoi, chi_nhanh):
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


def kiem_tra_nhan_ve_don(nguoi, don):
    """Ai được nhắn về đơn: khách chủ đơn, hoặc nhân sự phụ trách chi nhánh của đơn."""
    if _la_khach(nguoi):
        if don.khach_hang_id != nguoi.pk:
            raise PermissionDenied("Đơn không thuộc tài khoản của bạn.")
    elif not duoc_phu_trach_chi_nhanh(nguoi, don.chi_nhanh_id):
        raise PermissionDenied("Bạn không phụ trách chi nhánh của đơn này.")


def _mo_phong_don(nguoi, don):
    kiem_tra_nhan_ve_don(nguoi, don)
    return _lay_hoac_tao(
        khach_hang_id=don.khach_hang_id,
        chi_nhanh_id=don.chi_nhanh_id,
        don_hang=don,
        loai_cuoc_tro_chuyen="don_hang",
    )


def mo_phong(nguoi, chi_nhanh):
    """Dùng trong kiểm thử/dữ liệu mẫu; giao diện luôn đi qua bat_dau_tu_van."""
    return _mo_phong_tu_van(nguoi, chi_nhanh)[0]


def mo_phong_don_hang(nguoi, don):
    """Dùng trong kiểm thử/dữ liệu mẫu; giao diện luôn đi qua bat_dau_ve_don."""
    return _mo_phong_don(nguoi, don)[0]


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


def _kiem_toc_do(nguoi):
    """Chống spam: chỉ áp cho khách, nhân sự trả lời không bị giới hạn."""
    if not _la_khach(nguoi):
        return
    mot_phut_truoc = timezone.now() - timedelta(minutes=1)
    da_gui = TinNhan.objects.filter(nguoi_gui=nguoi, thoi_diem_tao__gte=mot_phut_truoc).count()
    if da_gui >= GIOI_HAN_TIN_MOT_PHUT:
        raise ValidationError("Bạn gửi hơi nhanh. Vui lòng chờ khoảng một phút rồi gửi tiếp.")


def _kiem_so_phong_moi(nguoi):
    if not _la_khach(nguoi):
        return
    dau_ngay = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    da_mo = CuocTroChuyen.objects.filter(khach_hang=nguoi, thoi_diem_tao__gte=dau_ngay).count()
    if da_mo > GIOI_HAN_PHONG_MOT_NGAY:
        raise ValidationError(
            "Hôm nay bạn đã mở nhiều cuộc trò chuyện. Hãy nhắn tiếp trong cuộc trò chuyện đang có."
        )


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
    if not TinNhan.objects.filter(nguoi_gui=nguoi, ma_tin_nhan=ma).exists():
        # Gửi lại cùng mã sau khi mất mạng không tính là tin mới nên không bị giới hạn.
        _kiem_toc_do(nguoi)
    tin, da_tao = TinNhan.objects.get_or_create(
        nguoi_gui=nguoi,
        ma_tin_nhan=ma,
        defaults={"cuoc_tro_chuyen": phong, "noi_dung_tin_nhan": noi_dung},
    )
    if tin.cuoc_tro_chuyen_id != phong.pk or tin.noi_dung_tin_nhan != noi_dung:
        raise ValidationError("Mã đã được dùng cho tin nhắn khác.")
    if da_tao:
        khoa = CuocTroChuyen.objects.select_for_update().get(pk=phong.pk)
        ben = ben_cua(nguoi, khoa)
        khoa.tin_cuoi = tin
        cac_cot = ["tin_cuoi"]
        if ben == "khach" and khoa.da_xong:
            # Khách hỏi tiếp sau khi nhà thuốc đã đóng: mở lại để không bị bỏ sót.
            khoa.trang_thai_xu_ly = "dang_mo"
            khoa.thoi_diem_xong = None
            khoa.nguoi_danh_dau_xong = None
            cac_cot += ["trang_thai_xu_ly", "thoi_diem_xong", "nguoi_danh_dau_xong"]
        khoa.save(update_fields=cac_cot)
        phong.tin_cuoi_id = tin.pk
        phong.trang_thai_xu_ly = khoa.trang_thai_xu_ly
        # Người vừa trả lời chắc chắn đã xem mọi tin trước đó của phòng.
        _day_moc_da_doc(khoa, ben, tin.pk)
    return tin, da_tao


@transaction.atomic
def gui_tin_dau(nguoi, phong, noi_dung):
    """Tin gửi qua form HTTP (không qua WebSocket); vẫn báo phía bên kia tức thời."""
    from .phat_tin_hieu import phat_sau_khi_luu

    tin, da_tao = ghi_tin_nhan(nguoi, phong, str(uuid4()), noi_dung)
    if da_tao:
        phat_sau_khi_luu(nguoi, phong, tin)
    return tin


def _bat_dau(nguoi, mo, noi_dung):
    """Tạo (hoặc dùng lại) phòng và ghi tin đầu trong một giao dịch: tin lỗi thì không có phòng."""
    if not isinstance(noi_dung, str) or not cat_khoang_trang(noi_dung):
        raise ValidationError("Hãy nhập nội dung tin nhắn.")
    with transaction.atomic():
        phong, moi_tao = mo()
        if moi_tao:
            _kiem_so_phong_moi(nguoi)
        gui_tin_dau(nguoi, phong, noi_dung)
    return phong


def bat_dau_tu_van(nguoi, chi_nhanh, noi_dung):
    """Khách hỏi một nhà thuốc; đã có phòng tư vấn với nhà thuốc đó thì nhắn tiếp vào phòng cũ."""
    return _bat_dau(nguoi, lambda: _mo_phong_tu_van(nguoi, chi_nhanh), noi_dung)


def bat_dau_ve_don(nguoi, don, noi_dung):
    """Khách hoặc nhân sự nhắn về một đơn; phòng của đơn chỉ xuất hiện khi tin đầu được gửi."""
    return _bat_dau(nguoi, lambda: _mo_phong_don(nguoi, don), noi_dung)


def _dat_trang_thai(nguoi, phong, xong):
    kiem_tra_phong(nguoi, phong)
    if ben_cua(nguoi, phong) != "nha_thuoc":
        raise PermissionDenied("Chỉ nhà thuốc đổi trạng thái xử lý cuộc trò chuyện.")
    khoa = CuocTroChuyen.objects.select_for_update().get(pk=phong.pk)
    if khoa.da_xong != xong:
        khoa.trang_thai_xu_ly = "da_xong" if xong else "dang_mo"
        khoa.thoi_diem_xong = timezone.now() if xong else None
        khoa.nguoi_danh_dau_xong = nguoi if xong else None
        khoa.save(update_fields=["trang_thai_xu_ly", "thoi_diem_xong", "nguoi_danh_dau_xong"])
    return khoa


@transaction.atomic
def danh_dau_xong(nguoi, phong):
    """Nhân sự đóng cuộc trò chuyện đã giải quyết: phòng rời hàng chờ, khách nhắn lại thì mở lại."""
    return _dat_trang_thai(nguoi, phong, True)


@transaction.atomic
def mo_lai(nguoi, phong):
    return _dat_trang_thai(nguoi, phong, False)
