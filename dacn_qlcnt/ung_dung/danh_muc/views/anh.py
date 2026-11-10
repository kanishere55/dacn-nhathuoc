from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from ung_dung.chung.anh import tra_anh
from ung_dung.chung.permissions import co_quyen

from ..forms import TaiAnhForm
from ..models import AnhChiNhanh, AnhNoiDung, AnhThuoc
from ..selectors import CO_ANH, lay_danh_muc
from ..services import anh as dich_vu


@require_GET
def anh_thuoc(request, ma):
    anh = get_object_or_404(AnhThuoc.objects.select_related("thuoc"), pk=ma)
    return _tra_neu_duoc_xem(request, anh, anh.thuoc.dang_hoat_dong, "thuoc.xem")


@require_GET
def anh_chi_nhanh(request, ma):
    anh = get_object_or_404(AnhChiNhanh.objects.select_related("chi_nhanh"), pk=ma)
    return _tra_neu_duoc_xem(request, anh, anh.chi_nhanh.dang_hoat_dong, "chi_nhanh.xem")


def _tra_neu_duoc_xem(request, anh, dang_hoat_dong, quyen_xem):
    """Ảnh của mục đang hoạt động ai cũng xem; mục ngừng hoạt động chỉ nhân sự có quyền xem."""
    if dang_hoat_dong:
        return tra_anh(request, anh)
    if not co_quyen(request.user, quyen_xem):
        raise Http404
    return tra_anh(request, anh, cong_khai=False)


@require_GET
def anh_noi_dung(request, ma):
    return tra_anh(request, get_object_or_404(AnhNoiDung, pk=ma))


def _la_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _url_anh(loai, anh):
    ten = "danh_muc:anh_thuoc" if loai == "thuoc" else "danh_muc:anh_chi_nhanh"
    return reverse(ten, args=[anh.pk])


def _bieu_dien(loai, doi_tuong, anh, *, la_dai_dien=False):
    ten_khoa = "danh_muc:anh_dai_dien"
    return {
        "id": anh.pk,
        "url": _url_anh(loai, anh),
        "rong": anh.chieu_rong,
        "cao": anh.chieu_cao,
        "nguon": anh.nguon_anh,
        "url_xoa": reverse("danh_muc:anh_xoa", args=[loai, doi_tuong.pk, anh.pk]),
        "url_dai_dien": reverse(ten_khoa, args=[loai, doi_tuong.pk, anh.pk]),
        "la_dai_dien": la_dai_dien,
    }


def _danh_sach_anh(loai, doi_tuong):
    _, model_anh, ten_khoa = CO_ANH[loai]
    cac_anh = model_anh.objects.filter(**{ten_khoa: doi_tuong}).defer("noi_dung_anh")
    return [_bieu_dien(loai, doi_tuong, anh, la_dai_dien=so == 0) for so, anh in enumerate(cac_anh)]


def _phan_hoi(request, loai, doi_tuong, thanh_cong, thong_diep):
    """Gọi bằng fetch thì trả JSON kèm danh sách ảnh mới; gửi form thường thì chuyển trang."""
    if _la_ajax(request):
        du_lieu = {"ok": thanh_cong, "thong_diep": thong_diep}
        if thanh_cong or loai in CO_ANH:
            du_lieu["cac_anh"] = _danh_sach_anh(loai, doi_tuong)
        return JsonResponse(du_lieu, status=200 if thanh_cong else 400)
    (messages.success if thanh_cong else messages.error)(request, thong_diep)
    return redirect(f"danh_muc:{loai}_sua", ma=doi_tuong.pk)


def _lay_doi_tuong(request, loai, ma):
    if not co_quyen(request.user, f"{loai}.sua"):
        raise PermissionDenied("Bạn không có quyền sửa ảnh của mục này.")
    # Cùng phạm vi với trang sửa: nhân sự một chi nhánh không thấy đối tượng của chi nhánh khác.
    return get_object_or_404(lay_danh_muc(request.user, loai), pk=ma)


@require_POST
def tai_len(request, loai, ma):
    doi_tuong = _lay_doi_tuong(request, loai, ma)
    form = TaiAnhForm(request.POST, request.FILES)
    if not form.is_valid():
        loi = " ".join(form.errors.get("cac_anh", ["Ảnh không hợp lệ."]))
        return _phan_hoi(request, loai, doi_tuong, False, loi)
    try:
        so_anh = len(dich_vu.them_anh(request.user, loai, doi_tuong, form.cleaned_data["cac_anh"]))
    except ValidationError as loi:
        return _phan_hoi(request, loai, doi_tuong, False, " ".join(loi.messages))
    return _phan_hoi(request, loai, doi_tuong, True, f"Đã thêm {so_anh} ảnh.")


@require_POST
def xoa(request, loai, ma, id_anh):
    doi_tuong = _lay_doi_tuong(request, loai, ma)
    try:
        dich_vu.xoa_anh(request.user, loai, doi_tuong, id_anh)
    except ValidationError as loi:
        return _phan_hoi(request, loai, doi_tuong, False, " ".join(loi.messages))
    return _phan_hoi(request, loai, doi_tuong, True, "Đã xóa ảnh.")


@require_POST
def dat_dai_dien(request, loai, ma, id_anh):
    doi_tuong = _lay_doi_tuong(request, loai, ma)
    try:
        dich_vu.dat_anh_dai_dien(request.user, loai, doi_tuong, id_anh)
    except ValidationError as loi:
        return _phan_hoi(request, loai, doi_tuong, False, " ".join(loi.messages))
    return _phan_hoi(request, loai, doi_tuong, True, "Đã đổi ảnh đại diện.")


@require_POST
def tai_anh_noi_dung(request):
    """Trình soạn thảo gửi một ảnh, nhận lại đường dẫn để chèn vào nội dung."""
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "thong_diep": "Cần đăng nhập."}, status=401)
    tep = request.FILES.get("anh")
    if tep is None:
        return JsonResponse({"ok": False, "thong_diep": "Hãy chọn một ảnh."}, status=400)
    try:
        anh = dich_vu.luu_anh_noi_dung(request.user, tep)
    except ValidationError as loi:
        return JsonResponse({"ok": False, "thong_diep": " ".join(loi.messages)}, status=400)
    except PermissionDenied:
        return JsonResponse({"ok": False, "thong_diep": "Bạn không có quyền chèn ảnh."}, status=403)
    return JsonResponse(
        {
            "ok": True,
            "url": reverse("danh_muc:anh_noi_dung", args=[anh.pk]),
            "rong": anh.chieu_rong,
            "cao": anh.chieu_cao,
        }
    )
