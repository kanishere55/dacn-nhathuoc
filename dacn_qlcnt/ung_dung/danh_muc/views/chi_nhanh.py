from ung_dung.chung.permissions import yeu_cau_quyen

from .danh_muc import hien_danh_sach, hien_form


@yeu_cau_quyen("chi_nhanh.xem")
def danh_sach(request):
    return hien_danh_sach(request, "chi_nhanh")


@yeu_cau_quyen("chi_nhanh.sua")
def tao(request):
    return hien_form(request, "chi_nhanh")


@yeu_cau_quyen("chi_nhanh.sua")
def sua(request, ma):
    return hien_form(request, "chi_nhanh", ma)
