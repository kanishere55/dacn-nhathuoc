from ung_dung.chung.permissions import yeu_cau_quyen

from .danh_muc import hien_danh_sach, hien_form


@yeu_cau_quyen("thuoc.xem")
def danh_sach(request):
    return hien_danh_sach(request, "thuoc")


@yeu_cau_quyen("thuoc.sua")
def tao(request):
    return hien_form(request, "thuoc")


@yeu_cau_quyen("thuoc.sua")
def sua(request, ma):
    return hien_form(request, "thuoc", ma)
