from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from ..du_lieu_form import ton_theo_lo
from ..forms import DongXuatHuyFormSet, PhieuXuatHuyForm
from ..loi_dong import cac_dong_da_nhap, gan_loi
from ..models import PhieuXuatHuy
from ..selectors import lay_lo_het_han_con_ton, lay_phieu
from ..services.phieu_xuat_huy import xuat_huy
from . import chung_tu


@yeu_cau_quyen("xuat_huy.xem")
def danh_sach(request):
    return chung_tu.hien_danh_sach(
        request,
        PhieuXuatHuy,
        lay_phieu(request.user, PhieuXuatHuy),
        tieu_de="Xuất hủy",
        url_tao="kho:phieu_xuat_huy_tao" if co_quyen(request.user, "xuat_huy.tao") else None,
        url_chi_tiet="kho:phieu_xuat_huy_chi_tiet",
    )


def _lap_san_het_han(request, cac_cn):
    """Điền sẵn mọi lô quá hạn còn tồn của đúng chi nhánh đang xem; quản lý vẫn xem lại rồi lưu.

    Người phụ trách nhiều chi nhánh mà chưa chọn chi nhánh thì không tự lấy chi nhánh đầu tiên,
    trả về danh sách chi nhánh kèm số lô quá hạn để chọn.
    """
    ma_cn = request.GET.get("chi_nhanh", "")
    if ma_cn.isascii() and ma_cn.isdecimal():
        chi_nhanh = cac_cn.filter(pk=ma_cn).first()
    else:
        hai = list(cac_cn[:2])
        chi_nhanh = hai[0] if len(hai) == 1 else None
    if chi_nhanh is None:
        cac_lua_chon = [
            {"chi_nhanh": cn, "so_lo": lay_lo_het_han_con_ton(cn).count()} for cn in cac_cn
        ]
        return None, None, cac_lua_chon
    cac_ton = list(lay_lo_het_han_con_ton(chi_nhanh)[:50])
    if not cac_ton:
        messages.info(
            request,
            f"{chi_nhanh.ten_chi_nhanh} không có lô nào đã hết hạn còn hàng có thể hủy "
            "(lô đang giữ cho đơn của khách phải chờ đơn xong).",
        )
    ban_dau = {"chi_nhanh": chi_nhanh, "loai_xuat_huy": "het_han"}
    return ban_dau, [{"lo_thuoc": t.lo_thuoc, "so_luong": t.kha_dung} for t in cac_ton], None


@yeu_cau_quyen("xuat_huy.tao")
def tao(request):
    ban_dau, ban_dau_dong, chon_chi_nhanh = None, None, None
    cac_cn = lay_chi_nhanh(request.user)
    if request.method == "GET" and request.GET.get("loai") == "het_han":
        ban_dau, ban_dau_dong, chon_chi_nhanh = _lap_san_het_han(request, cac_cn)
    form = PhieuXuatHuyForm(request.POST or None, initial=ban_dau, nguoi=request.user)
    cac_dong = DongXuatHuyFormSet(
        request.POST or None, initial=ban_dau_dong, form_kwargs={"nguoi": request.user}
    )
    if request.method == "POST" and form.is_valid() and cac_dong.is_valid():
        da_nhap = cac_dong_da_nhap(cac_dong)
        try:
            phieu = xuat_huy(
                request.user,
                form.cleaned_data["chi_nhanh"],
                form.cleaned_data["loai_xuat_huy"],
                [du_lieu for _, du_lieu in da_nhap],
                form.cleaned_data["ghi_chu"],
                khoa_yeu_cau=form.cleaned_data["khoa_yeu_cau"],
            )
        except ValidationError as loi:
            gan_loi(form, [dong for dong, _ in da_nhap], loi)
        else:
            return redirect("kho:phieu_xuat_huy_chi_tiet", ma=phieu.pk)
    return render(
        request,
        "kho/form_phieu.html",
        {
            "form": form,
            "cac_dong": cac_dong,
            "tieu_de": "Xuất hủy hàng",
            "mo_ta": (
                "Loại khỏi kho thuốc đã hết hạn, hư hỏng hoặc lô bị khóa bán theo thông báo thu "
                "hồi. Ghi số biên bản (và số văn bản thu hồi) để đối chiếu khi kiểm tra."
            ),
            "nhan_dong": "Lô cần hủy",
            "nhan_xac_nhan": "Lưu phiếu xuất hủy",
            "url_danh_sach": "kho:phieu_xuat_huy_danh_sach",
            "url_lap_san": "kho:phieu_xuat_huy_tao",
            "chon_chi_nhanh_lap_san": chon_chi_nhanh,
            "du_lieu_form": {"ton_lo": ton_theo_lo(cac_cn), "o_chi_nhanh": "chi_nhanh"},
        },
    )


def _phieu(request, ma):
    return get_object_or_404(lay_phieu(request.user, PhieuXuatHuy), pk=ma)


@yeu_cau_quyen("xuat_huy.xem")
def chi_tiet(request, ma):
    return chung_tu.hien_thi(request, _phieu(request, ma))


@yeu_cau_quyen("xuat_huy.xem")
def pdf(request, ma):
    return chung_tu.tra_pdf(request, _phieu(request, ma))
