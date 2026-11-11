from datetime import date

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen

from ..du_lieu_form import du_lieu_thuoc
from ..forms import DongNhapFormSet, PhieuNhapForm, TepNhapExcelForm
from ..loi_dong import cac_dong_da_nhap, gan_loi
from ..models import PhieuNhap
from ..nhap_excel import tao_tep_mau
from ..quy_tac import SO_NGAY_CAN_HAN, la_can_han
from ..selectors import lay_phieu, lay_phieu_nhap_danh_sach
from ..services.phieu_nhap import nhap_hang
from . import chung_tu

NHAN_LUU = "Lưu phiếu nhập"


@yeu_cau_quyen("phieu_nhap.xem")
def danh_sach(request):
    return chung_tu.hien_danh_sach(
        request,
        PhieuNhap,
        lay_phieu_nhap_danh_sach(request.user),
        tieu_de="Phiếu nhập",
        cac_cot=(
            ("Nhà cung cấp", "ten_nha_cung_cap", "chu"),
            ("Giá trị nhập", "gia_tri_nhap", "tien"),
        ),
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
        da_nhap = cac_dong_da_nhap(cac_dong)
        try:
            phieu = nhap_hang(
                request.user,
                form.cleaned_data["chi_nhanh"],
                form.cleaned_data["nha_cung_cap"],
                [du_lieu for _, du_lieu in da_nhap],
                form.cleaned_data["ghi_chu"],
                so_hoa_don_nha_cung_cap=form.cleaned_data["so_hoa_don_nha_cung_cap"],
                khoa_yeu_cau=form.cleaned_data["khoa_yeu_cau"],
            )
        except ValidationError as loi:
            gan_loi(form, [dong for dong, _ in da_nhap], loi)
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
    so_can_han = sum(la_can_han(date.fromisoformat(dong["ngay_het_han"])) for dong in cac_dong)
    loi_nhac = (
        f" Có {so_can_han} lô còn hạn dưới {SO_NGAY_CAN_HAN} ngày: tick “Vẫn nhận lô cận hạn” ở "
        "các dòng đó nếu đồng ý nhận."
        if so_can_han
        else ""
    )
    messages.info(
        request,
        f"Đã đọc {len(cac_dong)} dòng từ tệp. Kiểm tra lại, chọn nhà cung cấp rồi bấm "
        f"“{NHAN_LUU}”; kho chưa thay đổi.{loi_nhac}",
    )
    return _trang_tao(request, form, DongNhapFormSet(initial=cac_dong), TepNhapExcelForm())


def _trang_tao(request, form, cac_dong, form_excel):
    return render(
        request,
        "kho/form_phieu.html",
        {
            "form": form,
            "cac_dong": cac_dong,
            "form_excel": form_excel,
            "tieu_de": "Nhập hàng",
            "mo_ta": (
                "Ghi nhận hàng nhà cung cấp giao tới. Mỗi dòng là một lô có mã lô và hạn dùng in "
                "trên bao bì; giá nhập tính theo đơn vị cơ sở của thuốc."
            ),
            "nhan_dong": "Các lô nhận được",
            "nhan_xac_nhan": NHAN_LUU,
            "url_danh_sach": "kho:phieu_nhap_danh_sach",
            "co_thanh_tien": True,
            "du_lieu_form": {"thuoc": du_lieu_thuoc(), "so_ngay_can_han": SO_NGAY_CAN_HAN},
        },
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
