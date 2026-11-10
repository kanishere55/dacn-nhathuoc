from ung_dung.chung.permissions import yeu_cau_quyen

from .danh_muc import hien_danh_sach, hien_form


@yeu_cau_quyen("quy_doi_bao_goi.xem")
def danh_sach(request):
    return hien_danh_sach(request, "quy_doi_bao_goi")


@yeu_cau_quyen("quy_doi_bao_goi.sua")
def tao(request):
    return hien_form(request, "quy_doi_bao_goi")


@yeu_cau_quyen("quy_doi_bao_goi.sua")
def sua(request, ma):
    return hien_form(request, "quy_doi_bao_goi", ma)
