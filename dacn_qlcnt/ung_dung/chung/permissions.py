from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def la_quan_tri(nguoi):
    if not nguoi.is_authenticated or not nguoi.is_active:
        return False
    vai_tro = getattr(nguoi, "vai_tro", None)
    return vai_tro == "quan_tri_chuoi" if vai_tro is not None else nguoi.la_quan_tri_he_thong


def kiem_tra_vai_tro(nguoi, *vai_tro):
    if not nguoi.is_authenticated or not nguoi.is_active:
        raise PermissionDenied("Cần đăng nhập tài khoản đang hoạt động.")
    if not la_quan_tri(nguoi) and nguoi.vai_tro not in vai_tro:
        raise PermissionDenied("Bạn không có quyền thực hiện thao tác này.")


def kiem_tra_chi_nhanh(nguoi, chi_nhanh, *, quan_ly=False):
    kiem_tra_vai_tro(
        nguoi, *(("quan_ly_chi_nhanh",) if quan_ly else ("quan_ly_chi_nhanh", "nhan_vien"))
    )
    if not la_quan_tri(nguoi) and nguoi.chi_nhanh_id != chi_nhanh.pk:
        raise PermissionDenied("Chi nhánh không thuộc phạm vi của bạn.")


def yeu_cau_vai_tro(*vai_tro):
    def boc(ham):
        @wraps(ham)
        def xu_ly(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("tai_khoan:dang_nhap")
            kiem_tra_vai_tro(request.user, *vai_tro)
            return ham(request, *args, **kwargs)

        return xu_ly

    return boc
