from ung_dung.chung.permissions import yeu_cau_quyen

from .danh_muc import hien_danh_sach, hien_form


@yeu_cau_quyen("danh_muc_san_pham.xem")
def danh_sach(request):
    return hien_danh_sach(request, "danh_muc_san_pham")


@yeu_cau_quyen("danh_muc_san_pham.sua")
def tao(request):
    return hien_form(request, "danh_muc_san_pham")


@yeu_cau_quyen("danh_muc_san_pham.sua")
def sua(request, ma):
    return hien_form(request, "danh_muc_san_pham", ma)
