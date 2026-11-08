from ung_dung.chung.permissions import NHAN_SU_CHUOI, yeu_cau_vai_tro

from .danh_muc import hien_danh_sach, hien_form


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def danh_sach(request):
    return hien_danh_sach(request, "nha_cung_cap")


@yeu_cau_vai_tro("quan_tri_chuoi")
def tao(request):
    return hien_form(request, "nha_cung_cap")


@yeu_cau_vai_tro("quan_tri_chuoi")
def sua(request, ma):
    return hien_form(request, "nha_cung_cap", ma)
