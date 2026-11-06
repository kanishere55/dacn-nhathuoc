from django.db.models import QuerySet

from .models import CuocTroChuyen, TinNhan
from .permissions import kiem_tra_phong


def lay_cac_phong(nguoi) -> QuerySet:
    cac_phong = CuocTroChuyen.objects.select_related("khach_hang", "chi_nhanh").order_by("-pk")
    if not nguoi.is_authenticated or not nguoi.is_active:
        return cac_phong.none()
    if nguoi.vai_tro == "khach_hang":
        return cac_phong.filter(khach_hang=nguoi)
    if nguoi.vai_tro in {"nhan_vien", "quan_ly_chi_nhanh"} and nguoi.chi_nhanh_id:
        return cac_phong.filter(chi_nhanh_id=nguoi.chi_nhanh_id)
    return cac_phong.none()


def bieu_dien_tin(tin):
    return {
        "id_tin_nhan": tin.pk,
        "nguoi_gui": tin.nguoi_gui.ten_dang_nhap,
        "noi_dung": tin.noi_dung_tin_nhan,
        "thoi_diem": tin.thoi_diem_tao.isoformat(),
    }


def lay_lich_su(nguoi, phong):
    kiem_tra_phong(nguoi, phong)
    tin_nhan = (
        TinNhan.objects.filter(cuoc_tro_chuyen=phong).select_related("nguoi_gui").order_by("-pk")
    )
    return [bieu_dien_tin(tin) for tin in reversed(list(tin_nhan[:100]))]
