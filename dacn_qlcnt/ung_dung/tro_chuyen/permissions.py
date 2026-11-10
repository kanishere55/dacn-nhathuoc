from django.core.exceptions import PermissionDenied

from ung_dung.chung.permissions import co_quyen, thay_toan_chuoi


def duoc_phu_trach_chi_nhanh(nguoi, chi_nhanh_id):
    """Nhân sự có quyền trò chuyện và thuộc chi nhánh (hoặc xem toàn chuỗi)."""
    return bool(
        nguoi
        and nguoi.is_authenticated
        and nguoi.is_active
        and nguoi.vai_tro != "khach_hang"
        and co_quyen(nguoi, "tro_chuyen.dung")
        and (thay_toan_chuoi(nguoi) or nguoi.chi_nhanh_id == chi_nhanh_id)
    )


def kiem_tra_phong(nguoi, phong):
    if nguoi and nguoi.is_authenticated and nguoi.is_active:
        if nguoi.vai_tro == "khach_hang" and phong.khach_hang_id == nguoi.pk:
            return
        if duoc_phu_trach_chi_nhanh(nguoi, phong.chi_nhanh_id):
            return
    raise PermissionDenied("Bạn không thuộc cuộc trò chuyện này.")
