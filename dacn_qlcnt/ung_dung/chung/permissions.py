from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

NHAN_SU_CHI_NHANH = ("quan_ly_chi_nhanh", "nhan_vien")
NHAN_SU_CHUOI = ("quan_tri_chuoi", *NHAN_SU_CHI_NHANH)
MOI_VAI_TRO = ("khach_hang", *NHAN_SU_CHUOI)


def co_vai_tro(nguoi, *vai_tro):
    return nguoi.is_authenticated and nguoi.is_active and nguoi.vai_tro in vai_tro


def la_quan_tri(nguoi):
    return co_vai_tro(nguoi, "quan_tri_chuoi")


def kiem_tra_vai_tro(nguoi, *vai_tro):
    if not nguoi.is_authenticated or not nguoi.is_active:
        raise PermissionDenied("Cần đăng nhập tài khoản đang hoạt động.")
    if nguoi.vai_tro not in vai_tro:
        raise PermissionDenied("Bạn không có quyền thực hiện thao tác này.")


def co_quyen(nguoi, *ma_quyen):
    """Có ít nhất một trong các quyền; quản trị chuỗi luôn có mọi quyền."""
    return bool(
        nguoi.is_authenticated
        and nguoi.is_active
        and hasattr(nguoi, "co_quyen")
        and nguoi.co_quyen(*ma_quyen)
    )


def thay_toan_chuoi(nguoi):
    """Xem và thao tác trên mọi chi nhánh: quản trị chuỗi hoặc có quyền phạm vi toàn chuỗi."""
    return co_quyen(nguoi, "pham_vi.toan_chuoi")


def kiem_tra_quyen(nguoi, *ma_quyen):
    if not nguoi.is_authenticated or not nguoi.is_active:
        raise PermissionDenied("Cần đăng nhập tài khoản đang hoạt động.")
    if not co_quyen(nguoi, *ma_quyen):
        raise PermissionDenied("Bạn không có quyền thực hiện thao tác này.")


def kiem_tra_quyen_ghi_chi_nhanh(nguoi, chi_nhanh, *ma_quyen):
    """Cần một trong các quyền và đúng chi nhánh được phân công (trừ phạm vi toàn chuỗi)."""
    kiem_tra_quyen(nguoi, *ma_quyen)
    if not thay_toan_chuoi(nguoi) and nguoi.chi_nhanh_id != chi_nhanh.pk:
        raise PermissionDenied("Chi nhánh không thuộc phạm vi của bạn.")


def yeu_cau_quyen(*ma_quyen):
    def boc(ham):
        @wraps(ham)
        def xu_ly(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            kiem_tra_quyen(request.user, *ma_quyen)
            return ham(request, *args, **kwargs)

        return xu_ly

    return boc


def yeu_cau_vai_tro(*vai_tro):
    def boc(ham):
        @wraps(ham)
        def xu_ly(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            kiem_tra_vai_tro(request.user, *vai_tro)
            return ham(request, *args, **kwargs)

        return xu_ly

    return boc
