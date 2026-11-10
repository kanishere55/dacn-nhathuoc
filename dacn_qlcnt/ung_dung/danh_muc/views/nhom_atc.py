from ung_dung.chung.permissions import yeu_cau_quyen

from .danh_muc import hien_danh_sach, hien_form


@yeu_cau_quyen("nhom_atc.xem")
def danh_sach(request):
    return hien_danh_sach(request, "nhom_atc")


@yeu_cau_quyen("nhom_atc.sua")
def tao(request):
    return hien_form(request, "nhom_atc")


@yeu_cau_quyen("nhom_atc.sua")
def sua(request, ma):
    return hien_form(request, "nhom_atc", ma)
