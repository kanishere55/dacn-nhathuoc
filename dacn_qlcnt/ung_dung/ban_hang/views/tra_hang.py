"""Trả hàng: trang gửi yêu cầu của khách và trang xử lý của quản lý chi nhánh."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import OuterRef, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from ung_dung.chung.anh import tra_anh
from ung_dung.chung.loc_danh_sach import BoLoc, OChon, o_khoang_thoi_gian
from ung_dung.chung.permissions import (
    co_quyen,
    co_vai_tro,
    thay_toan_chuoi,
    yeu_cau_quyen,
    yeu_cau_vai_tro,
)
from ung_dung.danh_muc.models import AnhThuoc

from ..forms import TraHangForm, XuLyTraHangForm
from ..models import LY_DO_TRA_HANG, TRANG_THAI_TRA_HANG, AnhTraHang, YeuCauTraHang
from ..selectors import lay_don
from ..services import tra_hang as dich_vu

# Gợi ý khi khách nhập tên ngân hàng; khách vẫn gõ được ngân hàng khác.
NGAN_HANG_PHO_BIEN = (
    "Vietcombank",
    "VietinBank",
    "BIDV",
    "Agribank",
    "Techcombank",
    "MB Bank",
    "ACB",
    "VPBank",
    "Sacombank",
    "TPBank",
    "HDBank",
    "VIB",
    "SHB",
    "OCB",
    "MSB",
    "SeABank",
    "Eximbank",
    "LPBank",
    "Nam A Bank",
    "Bac A Bank",
)


def lay_yeu_cau(nguoi):
    tap_hop = YeuCauTraHang.objects.select_related(
        "don_hang__chi_nhanh", "don_hang__khach_hang", "nguoi_xu_ly"
    )
    if co_vai_tro(nguoi, "khach_hang"):
        return tap_hop.filter(don_hang__khach_hang=nguoi)
    if thay_toan_chuoi(nguoi):
        return tap_hop
    if co_quyen(nguoi, "tra_hang.xem", "tra_hang.duyet"):
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
                hoan_tien=form.thong_tin_hoan_tien(),
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            messages.success(request, f"Đã gửi yêu cầu {yeu_cau.ma_yeu_cau_tra_hang}.")
            return redirect("ban_hang:khach_don_hang_chi_tiet", ma=don.pk)
    return render(
        request,
        "ban_hang/khach/tra_hang.html",
        {
            "don": don,
            "form": form,
            "han": dich_vu.han_tra_hang(don),
            "so_anh_toi_da": dich_vu.SO_ANH_TOI_DA,
            "cac_ngan_hang": NGAN_HANG_PHO_BIEN,
        },
    )


def anh(request, ma):
    """Ảnh minh chứng riêng tư: chủ đơn hoặc nhân sự chi nhánh của đơn."""
    if not request.user.is_authenticated:
        raise Http404
    anh_tra = get_object_or_404(
        AnhTraHang.objects.filter(yeu_cau_tra_hang__in=lay_yeu_cau(request.user)), pk=ma
    )
    return tra_anh(request, anh_tra, cong_khai=False)


@yeu_cau_quyen("tra_hang.xem")
def danh_sach(request):
    loc = BoLoc(
        request,
        cac_cot_tim=(
            "ma_yeu_cau_tra_hang",
            "don_hang__ma_don_hang",
            "don_hang__khach_hang__ten_dang_nhap",
            "don_hang__khach_hang__ho_ten",
        ),
        nhan_tim="Mã yêu cầu, mã đơn, khách",
        cac_o_chon=[
            OChon("trang_thai", "Trạng thái", TRANG_THAI_TRA_HANG, "trang_thai"),
            OChon("ly_do", "Lý do", LY_DO_TRA_HANG, "ly_do"),
            o_khoang_thoi_gian("thoi_diem_tao", "Gửi trong"),
        ],
    )
    return render(
        request, "ban_hang/tra_hang_danh_sach.html", loc.ngu_canh(lay_yeu_cau(request.user))
    )


@yeu_cau_quyen("tra_hang.xem")
def chi_tiet(request, ma):
    yeu_cau = get_object_or_404(lay_yeu_cau(request.user), pk=ma)
    goi_y = dich_vu.so_luong_nhap_lai_goi_y(yeu_cau)
    return render(
        request,
        "ban_hang/tra_hang_chi_tiet.html",
        {
            "yc": yeu_cau,
            "cac_dong": [
                (dong, goi_y.get(dong.pk, 0))
                for dong in yeu_cau.cac_dong.select_related(
                    "chi_tiet_don_hang__thuoc__don_vi_tinh"
                ).prefetch_related("cac_phan_bo__phan_bo_phieu_ban__ton_kho__lo_thuoc")
            ],
            "cac_anh": yeu_cau.cac_anh.only("pk", "thu_tu"),
            "duoc_xu_ly": co_quyen(request.user, "tra_hang.duyet"),
        },
    )


@require_POST
@yeu_cau_quyen("tra_hang.duyet")
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
            nhap_lai = {}
            for dong in yeu_cau.cac_dong.all():
                gia_tri = request.POST.get(f"nhap_lai_{dong.pk}", "0").strip() or "0"
                if not gia_tri.isdecimal() or len(gia_tri) > 6:
                    raise ValidationError("Số lượng nhập lại kho phải là số nguyên không âm.")
                nhap_lai[dong.pk] = int(gia_tri)
            dich_vu.duyet(request.user, yeu_cau, du_lieu["ghi_chu"], nhap_lai=nhap_lai)
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
