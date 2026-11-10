from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen

from ..forms import DongNhapFormSet, PhieuNhapForm, TepNhapExcelForm
from ..models import PhieuNhap
from ..nhap_excel import tao_tep_mau
from ..selectors import lay_phieu
from ..services.phieu_nhap import nhap_hang
from . import chung_tu


@yeu_cau_quyen("phieu_nhap.xem")
def danh_sach(request):
    return chung_tu.hien_danh_sach(
        request,
        PhieuNhap,
        lay_phieu(request.user, PhieuNhap),
        tieu_de="Phiếu nhập",
        url_tao="kho:phieu_nhap_tao" if co_quyen(request.user, "phieu_nhap.tao") else None,
        url_chi_tiet="kho:phieu_nhap_chi_tiet",
    )


@yeu_cau_quyen("phieu_nhap.tao")
def tao(request):
    if request.method == "POST" and "doc_excel" in request.POST:
        return _xem_truoc_excel(request)
    form = PhieuNhapForm(request.POST or None, nguoi=request.user)
    cac_dong = DongNhapFormSet(request.POST or None)
    if request.method == "POST" and form.is_valid() and cac_dong.is_valid():
        try:
            phieu = nhap_hang(
                request.user,
                form.cleaned_data["chi_nhanh"],
                form.cleaned_data["nha_cung_cap"],
                [dong for dong in cac_dong.cleaned_data if dong and not dong.get("DELETE")],
                form.cleaned_data["ghi_chu"],
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("kho:phieu_nhap_chi_tiet", ma=phieu.pk)
    return _trang_tao(request, form, cac_dong, TepNhapExcelForm())


def _xem_truoc_excel(request):
    form_excel = TepNhapExcelForm(request.POST, request.FILES)
    form = PhieuNhapForm(
        initial={"chi_nhanh": request.user.chi_nhanh or request.POST.get("chi_nhanh") or None},
        nguoi=request.user,
    )
    if not form_excel.is_valid():
        return _trang_tao(request, form, DongNhapFormSet(), form_excel)
    cac_dong = form_excel.cleaned_data["tep_excel"]
    messages.info(
        request,
        f"Đã đọc {len(cac_dong)} dòng từ tệp. Kiểm tra lại, chọn nhà cung cấp rồi bấm "
        "“Xác nhận chứng từ”; kho chưa thay đổi.",
    )
    return _trang_tao(request, form, DongNhapFormSet(initial=cac_dong), TepNhapExcelForm())


def _trang_tao(request, form, cac_dong, form_excel):
    return render(
        request,
        "kho/form_phieu.html",
        {"form": form, "cac_dong": cac_dong, "tieu_de": "Nhập hàng", "form_excel": form_excel},
    )


@yeu_cau_quyen("phieu_nhap.tao")
def mau_excel(request):
    phan_hoi = HttpResponse(
        tao_tep_mau(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    phan_hoi["Content-Disposition"] = 'attachment; filename="mau-phieu-nhap.xlsx"'
    return phan_hoi


@yeu_cau_quyen("phieu_nhap.xem")
def chi_tiet(request, ma):
    return chung_tu.hien_thi(request, get_object_or_404(lay_phieu(request.user, PhieuNhap), pk=ma))


@yeu_cau_quyen("phieu_nhap.xem")
def pdf(request, ma):
    return chung_tu.tra_pdf(request, get_object_or_404(lay_phieu(request.user, PhieuNhap), pk=ma))
