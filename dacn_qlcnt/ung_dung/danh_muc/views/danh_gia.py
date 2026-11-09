"""Quản trị chuỗi kiểm duyệt đánh giá thuốc và chi nhánh: ẩn nhận xét vi phạm, không xóa."""

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ung_dung.chung.permissions import yeu_cau_vai_tro

from ..models import DanhGiaChiNhanh, DanhGiaThuoc

LOAI = {
    "thuoc": (DanhGiaThuoc, "thuoc", "danh_muc:danh_gia_doi_hien_thi"),
    "chi_nhanh": (DanhGiaChiNhanh, "chi_nhanh", "danh_muc:danh_gia_chi_nhanh_doi_hien_thi"),
}


@yeu_cau_vai_tro("quan_tri_chuoi")
def danh_sach(request):
    loai = request.GET.get("loai") if request.GET.get("loai") in LOAI else "thuoc"
    model, doi_tuong, url_doi = LOAI[loai]
    return render(
        request,
        "danh_muc/danh_gia_danh_sach.html",
        {
            "loai": loai,
            "url_doi_hien_thi": url_doi,
            "trang": Paginator(model.objects.select_related(doi_tuong, "khach_hang"), 30).get_page(
                request.GET.get("page")
            ),
        },
    )


def _doi(request, model, ma):
    danh_gia = get_object_or_404(model, pk=ma)
    danh_gia.dang_hien_thi = not danh_gia.dang_hien_thi
    danh_gia.save(update_fields=["dang_hien_thi"])
    tiep = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(tiep, allowed_hosts={request.get_host()}):
        return redirect(tiep)
    return redirect("danh_muc:danh_gia_danh_sach")


@require_POST
@yeu_cau_vai_tro("quan_tri_chuoi")
def doi_hien_thi(request, ma):
    return _doi(request, DanhGiaThuoc, ma)


@require_POST
@yeu_cau_vai_tro("quan_tri_chuoi")
def doi_hien_thi_chi_nhanh(request, ma):
    return _doi(request, DanhGiaChiNhanh, ma)
