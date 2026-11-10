from ung_dung.chung.permissions import yeu_cau_quyen

from .danh_muc import hien_danh_sach, hien_form


@yeu_cau_quyen("don_vi_tinh.xem")
def danh_sach(request):
    return hien_danh_sach(request, "don_vi_tinh")


@yeu_cau_quyen("don_vi_tinh.sua")
def tao(request):
    return hien_form(request, "don_vi_tinh")


@yeu_cau_quyen("don_vi_tinh.sua")
def sua(request, ma):
    return hien_form(request, "don_vi_tinh", ma)
