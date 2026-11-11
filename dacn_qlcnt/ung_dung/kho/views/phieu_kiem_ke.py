from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from ..forms import DongKiemKeFormSet, PhieuKiemKeForm
from ..models import PhieuKiemKe
from ..selectors import lay_phieu, lay_so_du, lay_ton_kiem_ke
from ..services.phieu_kiem_ke import LoiKiemKe, kiem_ke
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
    ca_lo_het = request.GET.get("ca_lo_het") == "1"
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
        cac_ton = list(lay_ton_kiem_ke(chi_nhanh).filter(pk__in=cac_ma_ton)) if chi_nhanh else []
    else:
        # Mặc định chỉ kiểm lô còn trên sổ; lô đã về 0 chỉ hiện khi người dùng chọn.
        trang = Paginator(
            lay_ton_kiem_ke(chi_nhanh, tu_khoa=tu_khoa, chi_con_hang=not ca_lo_het),
            DongKiemKeFormSet.max_num,
        )
        trang = trang.get_page(request.GET.get("page"))
        cac_ton = list(trang.object_list)
        ban_dau = [{"ton_kho": ton.pk, "so_luong_so_sach": ton.so_luong} for ton in cac_ton]
    _gan_dang_giu(chi_nhanh, cac_ton)
    tham_so_dong = {"nguoi": request.user, "ton_theo_id": {str(ton.pk): ton for ton in cac_ton}}
    cac_dong = DongKiemKeFormSet(du_lieu, initial=ban_dau, form_kwargs=tham_so_dong)
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
                khoa_yeu_cau=form.cleaned_data["khoa_yeu_cau"],
            )
        except LoiKiemKe as loi:
            cac_dong = _dem_lai_lo_phat_sinh(du_lieu, cac_dong, loi, tham_so_dong)
            form.add_error(
                None,
                f"Phiếu chưa được lưu: {len(loi.loi_theo_ton)} lô cần xem lại (tô đỏ bên dưới). "
                "Số đã đếm ở các lô khác vẫn giữ nguyên.",
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
            "ca_lo_het": ca_lo_het,
        },
    )


def _gan_dang_giu(chi_nhanh, cac_ton):
    """Lượng đang giữ cho đơn của từng lô, để cột "Đang giữ" cho biết số đếm tối thiểu."""
    if not chi_nhanh or not cac_ton:
        return
    giu = dict(
        lay_so_du(chi_nhanh=chi_nhanh)
        .filter(pk__in=[ton.pk for ton in cac_ton])
        .values_list("pk", "dang_giu")
    )
    for ton in cac_ton:
        ton.dang_giu = giu.get(ton.pk, 0)


def _dem_lai_lo_phat_sinh(du_lieu, cac_dong, loi, tham_so_dong):
    """Dựng lại bảng sau khi bị từ chối: lô vừa có phát sinh nhận số sổ sách mới và xóa số
    đếm (Q08: phải đếm lại lô đó); các lô khác giữ nguyên số đã nhập; lỗi gắn vào đúng lô."""
    du_lieu = du_lieu.copy()
    for dong in cac_dong.forms:
        ton = dong.cleaned_data.get("ton_kho")
        if ton is not None and ton.pk in loi.so_du_moi:
            du_lieu[f"{dong.prefix}-so_luong_so_sach"] = str(loi.so_du_moi[ton.pk])
            du_lieu[f"{dong.prefix}-so_luong_thuc_te"] = ""
    moi = DongKiemKeFormSet(du_lieu, form_kwargs=tham_so_dong)
    moi.is_valid()
    for dong in moi.forms:
        ton = dong.cleaned_data.get("ton_kho")
        if ton is not None and ton.pk in loi.loi_theo_ton:
            dong.can_dem_lai = ton.pk in loi.so_du_moi
            dong.add_error("so_luong_thuc_te", loi.loi_theo_ton[ton.pk])
    return moi


def _phieu(request, ma):
    return get_object_or_404(lay_phieu(request.user, PhieuKiemKe), pk=ma)


@yeu_cau_quyen("kiem_ke.xem")
def chi_tiet(request, ma):
    return chung_tu.hien_thi(request, _phieu(request, ma))


@yeu_cau_quyen("kiem_ke.xem")
def pdf(request, ma):
    return chung_tu.tra_pdf(request, _phieu(request, ma))
