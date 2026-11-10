from ung_dung.chung.permissions import yeu_cau_quyen

from .danh_muc import hien_danh_sach, hien_form


@yeu_cau_quyen("nhan_vien.xem")
def danh_sach(request):
    return hien_danh_sach(request, "nhan_vien")


@yeu_cau_quyen("nhan_vien.sua")
def tao(request):
    return hien_form(request, "nhan_vien")


@yeu_cau_quyen("nhan_vien.sua")
def sua(request, ma):
    return hien_form(request, "nhan_vien", ma)
