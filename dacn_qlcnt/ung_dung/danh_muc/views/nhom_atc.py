from ung_dung.chung.permissions import yeu_cau_vai_tro

from .danh_muc import hien_danh_sach, hien_form


@yeu_cau_vai_tro("quan_ly_chi_nhanh", "nhan_vien")
def danh_sach(request):
    return hien_danh_sach(request, "nhom_atc")


@yeu_cau_vai_tro("quan_tri_chuoi")
def tao(request):
    return hien_form(request, "nhom_atc")


@yeu_cau_vai_tro("quan_tri_chuoi")
def sua(request, ma):
    return hien_form(request, "nhom_atc", ma)
