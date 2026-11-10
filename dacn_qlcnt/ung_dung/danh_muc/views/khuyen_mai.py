from ung_dung.chung.permissions import yeu_cau_quyen

from .danh_muc import hien_danh_sach, hien_form


@yeu_cau_quyen("khuyen_mai.xem")
def danh_sach(request):
    return hien_danh_sach(request, "khuyen_mai")


@yeu_cau_quyen("khuyen_mai.sua")
def tao(request):
    return hien_form(request, "khuyen_mai")


@yeu_cau_quyen("khuyen_mai.sua")
def sua(request, ma):
    return hien_form(request, "khuyen_mai", ma)
