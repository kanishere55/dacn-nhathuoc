"""Trang chi tiết và bản PDF dùng chung cho mọi loại chứng từ kho."""

from functools import reduce

from django.http import HttpResponse
from django.shortcuts import render

from ung_dung.thong_bao.services import ten_thuong_hieu

from ..chung_tu import du_lieu_chung_tu, ten_tep_pdf, ve_pdf
from ..loc import loc_phieu


def hien_danh_sach(
    request, model, cac_phieu, *, tieu_de, url_tao, url_chi_tiet, chi_nhanh="chi_nhanh"
):
    """Danh sách chứng từ có tìm kiếm, lọc theo chi nhánh/thời gian và phân trang."""
    loc = loc_phieu(request, model, chi_nhanh)
    cac_phieu = cac_phieu.select_related("nguoi_lap", chi_nhanh)
    ngu_canh = loc.ngu_canh(cac_phieu)
    for phieu in ngu_canh["trang"]:
        phieu.chi_nhanh_hien = reduce(getattr, chi_nhanh.split("__"), phieu)
    return render(
        request,
        "kho/danh_sach_phieu.html",
        {
            **ngu_canh,
            "tieu_de": tieu_de,
            "url_tao": url_tao,
            "url_chi_tiet": url_chi_tiet,
        },
    )


def hien_thi(request, phieu):
    chung_tu = du_lieu_chung_tu(phieu)
    return render(
        request,
        "kho/chi_tiet_phieu.html",
        {
            "chung_tu": chung_tu,
            "url_danh_sach": f"kho:{chung_tu['ten']}_danh_sach",
            "url_pdf": f"kho:{chung_tu['ten']}_pdf",
        },
    )


def tra_pdf(request, phieu):
    chung_tu = du_lieu_chung_tu(phieu)
    phan_hoi = HttpResponse(ve_pdf(chung_tu, ten_thuong_hieu()), content_type="application/pdf")
    kieu = "attachment" if "tai" in request.GET else "inline"
    phan_hoi["Content-Disposition"] = f'{kieu}; filename="{ten_tep_pdf(chung_tu)}"'
    phan_hoi["Cache-Control"] = "private, no-store"
    return phan_hoi
