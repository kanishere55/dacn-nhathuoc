"""Trả hàng: trang gửi yêu cầu của khách và trang xử lý của quản lý chi nhánh."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import OuterRef, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from ung_dung.chung.anh import tra_anh
from ung_dung.chung.permissions import (
    NHAN_SU_CHUOI,
    co_vai_tro,
    la_quan_tri,
    yeu_cau_vai_tro,
)
from ung_dung.danh_muc.models import AnhThuoc

from ..forms import TraHangForm, XuLyTraHangForm
from ..models import TRANG_THAI_TRA_HANG, AnhTraHang, YeuCauTraHang
from ..selectors import lay_don
from ..services import tra_hang as dich_vu


def lay_yeu_cau(nguoi):
    tap_hop = YeuCauTraHang.objects.select_related(
        "don_hang__chi_nhanh", "don_hang__khach_hang", "nguoi_xu_ly"
    )
    if co_vai_tro(nguoi, "khach_hang"):
        return tap_hop.filter(don_hang__khach_hang=nguoi)
    if la_quan_tri(nguoi):
        return tap_hop
    if co_vai_tro(nguoi, *NHAN_SU_CHUOI):
        return tap_hop.filter(don_hang__chi_nhanh_id=nguoi.chi_nhanh_id)
    return tap_hop.none()


@yeu_cau_vai_tro("khach_hang")
@require_http_methods(["GET", "POST"])
def khach_tao(request, ma):
    don = get_object_or_404(lay_don(request.user), pk=ma)
    chan = dich_vu.ly_do_khong_tra_duoc(don)
    if chan:
        messages.error(request, chan)
        return redirect("ban_hang:khach_don_hang_chi_tiet", ma=don.pk)
    form = TraHangForm(
        request.POST or None,
        request.FILES or None,
        cac_dong=don.cac_dong.select_related("thuoc__don_vi_tinh").annotate(
            id_anh=Subquery(
                AnhThuoc.objects.filter(thuoc=OuterRef("thuoc"))
                .order_by("thu_tu", "pk")
                .values("pk")[:1]
            )
        ),
        con_lai=dich_vu.so_luong_con_tra(don),
    )
    if request.method == "POST" and form.is_valid():
        try:
            yeu_cau = dich_vu.tao_yeu_cau(
                request.user,
                don,
                ly_do=form.cleaned_data["ly_do"],
                mo_ta=form.cleaned_data["mo_ta"],
                cac_dong=form.cac_dong_tra(),
                cac_anh=form.cleaned_data["cac_anh"],
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            messages.success(request, f"Đã gửi yêu cầu {yeu_cau.ma_yeu_cau_tra_hang}.")
            return redirect("ban_hang:khach_don_hang_chi_tiet", ma=don.pk)
    return render(
        request,
        "ban_hang/khach/tra_hang.html",
        {"don": don, "form": form, "han": dich_vu.han_tra_hang(don)},
    )


def anh(request, ma):
    """Ảnh minh chứng riêng tư: chủ đơn hoặc nhân sự chi nhánh của đơn."""
    if not request.user.is_authenticated:
        raise Http404
    anh_tra = get_object_or_404(
        AnhTraHang.objects.filter(yeu_cau_tra_hang__in=lay_yeu_cau(request.user)), pk=ma
    )
    return tra_anh(request, anh_tra, cong_khai=False)


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def danh_sach(request):
    trang_thai = request.GET.get("trang_thai", "cho_duyet")
    cac_yeu_cau = lay_yeu_cau(request.user)
    if trang_thai in dict(TRANG_THAI_TRA_HANG):
        cac_yeu_cau = cac_yeu_cau.filter(trang_thai=trang_thai)
    else:
        trang_thai = ""
    return render(
        request,
        "ban_hang/tra_hang_danh_sach.html",
        {
            "trang": Paginator(cac_yeu_cau, 25).get_page(request.GET.get("page")),
            "trang_thai": trang_thai,
            "cac_trang_thai": TRANG_THAI_TRA_HANG,
        },
    )


@yeu_cau_vai_tro(*NHAN_SU_CHUOI)
def chi_tiet(request, ma):
    yeu_cau = get_object_or_404(lay_yeu_cau(request.user), pk=ma)
    return render(
        request,
        "ban_hang/tra_hang_chi_tiet.html",
        {
            "yc": yeu_cau,
            "cac_dong": yeu_cau.cac_dong.select_related("chi_tiet_don_hang__thuoc__don_vi_tinh"),
            "cac_anh": yeu_cau.cac_anh.only("pk", "thu_tu"),
            "duoc_xu_ly": co_vai_tro(request.user, "quan_ly_chi_nhanh"),
        },
    )


@require_POST
@yeu_cau_vai_tro("quan_ly_chi_nhanh")
def xu_ly(request, ma, hanh_dong):
    yeu_cau = get_object_or_404(lay_yeu_cau(request.user), pk=ma)
    form = XuLyTraHangForm(request.POST)
    if not form.is_valid():
        for loi in form.errors.values():
            messages.error(request, " ".join(loi))
        return redirect("ban_hang:tra_hang_chi_tiet", ma=ma)
    du_lieu = form.cleaned_data
    try:
        if hanh_dong == "duyet":
            dich_vu.duyet(request.user, yeu_cau, du_lieu["ghi_chu"])
            messages.success(request, "Đã duyệt yêu cầu, hãy hoàn tiền cho khách.")
        elif hanh_dong == "tu_choi":
            dich_vu.tu_choi(request.user, yeu_cau, du_lieu["ghi_chu"])
            messages.success(request, "Đã từ chối yêu cầu.")
        elif hanh_dong == "hoan_tien":
            dich_vu.hoan_tien_tra_hang(
                request.user,
                yeu_cau,
                phuong_thuc=du_lieu["phuong_thuc"] or "chuyen_khoan",
                ma_tham_chieu=du_lieu["ma_tham_chieu"],
            )
            messages.success(request, "Đã ghi nhận hoàn tiền.")
        else:
            raise Http404
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    return redirect("ban_hang:tra_hang_chi_tiet", ma=ma)
