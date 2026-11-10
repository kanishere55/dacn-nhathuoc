from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from ..forms import DongKiemKeFormSet, PhieuKiemKeForm
from ..models import PhieuKiemKe
from ..selectors import lay_phieu, lay_ton_kiem_ke
from ..services.phieu_kiem_ke import kiem_ke
from . import chung_tu


@yeu_cau_quyen("kiem_ke.xem")
def danh_sach(request):
    return chung_tu.hien_danh_sach(
        request,
        PhieuKiemKe,
        lay_phieu(request.user, PhieuKiemKe),
        tieu_de="Kiểm kê",
        url_tao="kho:phieu_kiem_ke_tao" if co_quyen(request.user, "kiem_ke.tao") else None,
        url_chi_tiet="kho:phieu_kiem_ke_chi_tiet",
    )


@yeu_cau_quyen("kiem_ke.tao")
@require_http_methods(["GET", "POST"])
def tao(request):
    cac_chi_nhanh = list(lay_chi_nhanh(request.user))
    du_lieu = request.POST if request.method == "POST" else None
    ma = (du_lieu if du_lieu is not None else request.GET).get("chi_nhanh")
    mac_dinh = cac_chi_nhanh[0] if du_lieu is None and cac_chi_nhanh else None
    chi_nhanh = next((cn for cn in cac_chi_nhanh if str(cn.pk) == ma), mac_dinh)
    form = PhieuKiemKeForm(du_lieu, nguoi=request.user, initial={"chi_nhanh": chi_nhanh})
    tu_khoa = request.GET.get("q", "").strip()[:150]
    trang = None
    ban_dau = []
    if form.is_bound:
        cac_ma_ton = {
            int(gia_tri)
            for ten, gia_tri in du_lieu.items()
            if ten.startswith("form-")
            and ten.endswith("-ton_kho")
            and len(gia_tri) <= 19
            and gia_tri.isascii()
            and gia_tri.isdecimal()
        }
        cac_ton = lay_ton_kiem_ke(chi_nhanh).filter(pk__in=cac_ma_ton) if chi_nhanh else ()
    else:
        trang = Paginator(lay_ton_kiem_ke(chi_nhanh, tu_khoa=tu_khoa), DongKiemKeFormSet.max_num)
        trang = trang.get_page(request.GET.get("page"))
        cac_ton = list(trang.object_list)
        ban_dau = [{"ton_kho": ton.pk, "so_luong_so_sach": ton.so_luong} for ton in cac_ton]
    cac_dong = DongKiemKeFormSet(
        du_lieu,
        initial=ban_dau,
        form_kwargs={
            "nguoi": request.user,
            "ton_theo_id": {str(ton.pk): ton for ton in cac_ton},
        },
    )
    if form.is_bound and form.is_valid() and cac_dong.is_valid():
        try:
            phieu = kiem_ke(
                request.user,
                form.cleaned_data["chi_nhanh"],
                [
                    d
                    for d in cac_dong.cleaned_data
                    if d.get("so_luong_thuc_te") is not None and not d.get("DELETE")
                ],
                form.cleaned_data["ghi_chu"],
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("kho:phieu_kiem_ke_chi_tiet", ma=phieu.pk)
    return render(
        request,
        "kho/phieu_kiem_ke_form.html",
        {
            "form": form,
            "cac_dong": cac_dong,
            "cac_chi_nhanh": cac_chi_nhanh,
            "chi_nhanh_da_chon": chi_nhanh,
            "trang": trang,
            "tu_khoa": tu_khoa,
        },
    )


def _phieu(request, ma):
    return get_object_or_404(lay_phieu(request.user, PhieuKiemKe), pk=ma)


@yeu_cau_quyen("kiem_ke.xem")
def chi_tiet(request, ma):
    return chung_tu.hien_thi(request, _phieu(request, ma))


@yeu_cau_quyen("kiem_ke.xem")
def pdf(request, ma):
    return chung_tu.tra_pdf(request, _phieu(request, ma))
