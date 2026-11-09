"""Trang chi tiết và bản PDF dùng chung cho mọi loại chứng từ kho."""

from django.http import HttpResponse
from django.shortcuts import render

from ung_dung.thong_bao.services import ten_thuong_hieu

from ..chung_tu import du_lieu_chung_tu, ten_tep_pdf, ve_pdf


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
