from ung_dung.chung.permissions import yeu_cau_quyen

from .danh_muc import hien_danh_sach, hien_form


@yeu_cau_quyen("nha_cung_cap.xem")
def danh_sach(request):
    return hien_danh_sach(request, "nha_cung_cap")


@yeu_cau_quyen("nha_cung_cap.sua")
def tao(request):
    return hien_form(request, "nha_cung_cap")


@yeu_cau_quyen("nha_cung_cap.sua")
def sua(request, ma):
    return hien_form(request, "nha_cung_cap", ma)
