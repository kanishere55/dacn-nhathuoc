from django.core.exceptions import PermissionDenied


def kiem_tra_phong(nguoi, phong):
    if nguoi and nguoi.is_authenticated and nguoi.is_active:
        if nguoi.vai_tro == "khach_hang" and phong.khach_hang_id == nguoi.pk:
            return
        if (
            nguoi.vai_tro in {"nhan_vien", "quan_ly_chi_nhanh"}
            and nguoi.chi_nhanh_id == phong.chi_nhanh_id
        ):
            return
    raise PermissionDenied("Bạn không thuộc cuộc trò chuyện này.")
