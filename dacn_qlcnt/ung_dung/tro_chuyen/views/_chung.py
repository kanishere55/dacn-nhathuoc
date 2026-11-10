"""Hàm dùng chung cho view trò chuyện của hai khu (khách và /quan-ly/)."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ung_dung.chung.anh import tra_anh

from ..forms import GuiTinForm
from ..selectors import anh_xem_duoc, bieu_dien_tin, the_don
from ..services import gui_tin_http, kiem_tra_the
from ..the_dinh_kem import doc_the


def so_truoc(request):
    """Mốc `?truoc=<id tin>` khi tải tin cũ hơn; giá trị lạ coi như không có."""
    truoc = request.GET.get("truoc", "")
    return int(truoc) if truoc.isascii() and truoc.isdecimal() and len(truoc) <= 18 else None


def loi_dau_tien(form):
    for cac_loi in form.errors.values():
        return cac_loi[0]
    return "Không gửi được tin nhắn."


def gui_tin_kem_anh(request, phong):
    """POST multipart từ khung chat: tin có ảnh (kèm chữ, thẻ). Trả JSON tin đã lưu."""
    form = GuiTinForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"loi": loi_dau_tien(form)}, status=400)
    du_lieu = form.cleaned_data
    try:
        thuoc, don = doc_the(du_lieu.get("thuoc"), du_lieu.get("don_hang"))
        tin = gui_tin_http(
            request.user,
            phong,
            du_lieu["noi_dung"],
            ma=str(du_lieu["ma_tin_nhan"]),
            cac_anh=du_lieu["cac_anh"],
            thuoc=thuoc,
            don=don,
        )
    except ValidationError as loi:
        return JsonResponse({"loi": loi.messages[0]}, status=400)
    except PermissionDenied:
        return JsonResponse({"loi": "Bạn không còn quyền gửi tin trong cuộc này."}, status=403)
    return JsonResponse({"tin": bieu_dien_tin(tin, phong.khach_hang_id)})


def the_don_cho_gui(request, phong):
    """Thẻ đơn đang chờ gửi (?don=<id>), chỉ khi đơn thuộc đúng khách và chi nhánh của cuộc."""
    try:
        _, don = doc_the(None, request.GET.get("don"))
        if don is not None:
            kiem_tra_the(phong, don=don)
    except ValidationError:
        return None
    return {"id": don.pk, **the_don(don)} if don else None


def xem_anh(request, ma):
    """Ảnh riêng tư: chỉ người thuộc cuộc trò chuyện chứa ảnh mới mở được."""
    anh = get_object_or_404(anh_xem_duoc(request.user), pk=ma)
    return tra_anh(request, anh, cong_khai=False)
