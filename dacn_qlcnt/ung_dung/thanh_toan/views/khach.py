from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_GET, require_POST

from ung_dung.ban_hang.selectors import lay_don
from ung_dung.chung.permissions import yeu_cau_vai_tro

from .. import momo, vietqr
from ..models import GiaoDichThanhToan
from ..services.cong import xu_ly_ket_qua_momo
from ..services.ghi import tao_cho


def _don_cho(request, ma):
    return get_object_or_404(lay_don(request.user), pk=ma)


@yeu_cau_vai_tro("khach_hang")
@require_GET
def trang_thanh_toan(request, ma):
    don = _don_cho(request, ma)
    if don.trang_thai != "cho_thanh_toan" or don.qua_han_giu:
        return redirect("ban_hang:khach_don_hang_chi_tiet", ma=don.pk)
    ngu_canh = {"don": don, "han_giay": int(don.thoi_diem_het_giu.timestamp())}
    if don.phuong_thuc_thanh_toan == "chuyen_khoan":
        ngu_canh.update(
            {
                "qr_svg": mark_safe(vietqr.ve_svg(_chuoi_qr(don))),  # noqa: S308 - SVG do segno sinh
                "ten_ngan_hang": settings.TEN_NGAN_HANG,
                "so_tai_khoan": settings.SO_TAI_KHOAN,
                "ten_tai_khoan": settings.TEN_TAI_KHOAN,
            }
        )
    return render(request, "thanh_toan/khach/thanh_toan.html", ngu_canh)


def _chuoi_qr(don):
    return vietqr.tao_chuoi(
        settings.NGAN_HANG_BIN, settings.SO_TAI_KHOAN, don.tong_thanh_toan, don.ma_don_hang
    )


@yeu_cau_vai_tro("khach_hang")
@require_GET
def anh_qr(request, ma):
    """Ảnh PNG của mã VietQR để khách lưu vào máy và quét từ thư viện ảnh."""
    don = _don_cho(request, ma)
    if don.trang_thai != "cho_thanh_toan" or don.phuong_thuc_thanh_toan != "chuyen_khoan":
        raise Http404
    phan_hoi = HttpResponse(vietqr.ve_png(_chuoi_qr(don)), content_type="image/png")
    phan_hoi["Cache-Control"] = "private, no-store"
    return phan_hoi


@yeu_cau_vai_tro("khach_hang")
@require_GET
def trang_thai(request, ma):
    """HTMX hỏi định kỳ; khi đơn đã được thanh toán thì chuyển về trang đơn."""
    don = _don_cho(request, ma)
    if don.trang_thai != "cho_thanh_toan" or don.qua_han_giu:
        phan_hoi = render(request, "thanh_toan/khach/_trang_thai.html", {"don": don, "xong": True})
        phan_hoi["HX-Redirect"] = reverse("ban_hang:khach_don_hang_chi_tiet", args=[don.pk])
        return phan_hoi
    return render(request, "thanh_toan/khach/_trang_thai.html", {"don": don})


@yeu_cau_vai_tro("khach_hang")
@require_POST
def bat_dau_momo(request, ma):
    don = _don_cho(request, ma)
    if don.trang_thai != "cho_thanh_toan" or don.phuong_thuc_thanh_toan != "momo":
        return redirect("ban_hang:khach_don_hang_chi_tiet", ma=don.pk)
    # MoMo không nhận lại mã đơn đã gửi: mỗi lần bấm là một giao dịch chờ mới.
    GiaoDichThanhToan.objects.filter(don_hang=don, phuong_thuc="momo", trang_thai="cho").update(
        trang_thai="het_han", thoi_diem_hoan_tat=timezone.now()
    )
    giao_dich = tao_cho(don, "momo")
    try:
        url = momo.tao_thanh_toan(
            giao_dich.ma_giao_dich_thanh_toan,
            don.tong_thanh_toan,
            f"Thanh toan don {don.ma_don_hang}",
            request.build_absolute_uri(reverse("thanh_toan:momo_quay_ve")),
            request.build_absolute_uri(reverse("thanh_toan:momo_ipn")),
        )
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
        return redirect("thanh_toan:trang_thanh_toan", ma=don.pk)
    return redirect(url)


@require_GET
def momo_quay_ve(request):
    du_lieu = request.GET.dict()
    giao_dich = GiaoDichThanhToan.objects.filter(
        ma_giao_dich_thanh_toan=du_lieu.get("orderId", ""), phuong_thuc="momo"
    ).first()
    if giao_dich is None or not momo.kiem_chu_ky_ket_qua(du_lieu):
        messages.error(request, "Không xác thực được kết quả từ MoMo.")
        return redirect("ban_hang:khach_don_hang_danh_sach")
    ket_qua = xu_ly_ket_qua_momo(du_lieu)
    if ket_qua == "that_bai":
        messages.error(request, "Thanh toán MoMo chưa thành công. Bạn có thể thử lại.")
        return redirect("thanh_toan:trang_thanh_toan", ma=giao_dich.don_hang_id)
    messages.success(request, "Đã nhận thanh toán qua MoMo.")
    return redirect("ban_hang:khach_don_hang_chi_tiet", ma=giao_dich.don_hang_id)
