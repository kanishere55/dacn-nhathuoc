from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.ban_hang.forms import BoQuaTienForm, GanTienForm
from ung_dung.chung.loc_danh_sach import BoLoc, OChon
from ung_dung.chung.permissions import thay_toan_chuoi, yeu_cau_quyen

from ..models import NGUON_CONG_DEN, TRANG_THAI_CONG_DEN, GiaoDichCongDen
from ..services.cong import LOI_BAO_NHAN_TIEN, bo_qua_tien_chua_khop, gan_tien_vao_don


def _kiem_pham_vi(nguoi):
    if not thay_toan_chuoi(nguoi):
        raise PermissionDenied("Đối soát tiền chưa khớp cần quyền toàn chuỗi.")


@yeu_cau_quyen("thanh_toan.xac_nhan")
def danh_sach(request):
    _kiem_pham_vi(request.user)
    tap_hop = GiaoDichCongDen.objects.select_related("giao_dich_thanh_toan__don_hang")
    if "trang_thai" not in request.GET:
        tap_hop = tap_hop.filter(trang_thai="cho_khop")
    loc = BoLoc(
        request,
        cac_cot_tim=("ma_doi_tac", "ma_tham_chieu", "noi_dung_giao_dich"),
        nhan_tim="Mã giao dịch, nội dung chuyển tiền",
        cac_o_chon=[
            OChon("nguon", "Nguồn", NGUON_CONG_DEN, "nguon"),
            OChon("trang_thai", "Trạng thái", TRANG_THAI_CONG_DEN, "trang_thai"),
        ],
    )
    return render(request, "thanh_toan/tien_chua_khop.html", loc.ngu_canh(tap_hop))


@require_POST
@yeu_cau_quyen("thanh_toan.xac_nhan")
def xu_ly(request, ma, hanh_dong):
    _kiem_pham_vi(request.user)
    dong = get_object_or_404(GiaoDichCongDen, pk=ma)
    form = {"gan": GanTienForm, "bo-qua": BoQuaTienForm}[hanh_dong](request.POST)
    if form.is_valid():
        try:
            if hanh_dong == "gan":
                don, ket_qua = gan_tien_vao_don(request.user, dong, **form.cleaned_data)
                messages.success(request, f"{don.ma_don_hang} · {LOI_BAO_NHAN_TIEN[ket_qua]}")
            else:
                bo_qua_tien_chua_khop(request.user, dong, form.cleaned_data["ly_do"])
                messages.success(request, "Đã lưu cách xử lý khoản tiền.")
        except ValidationError as loi:
            messages.error(request, " ".join(loi.messages))
    else:
        for loi in form.errors.values():
            messages.error(request, " ".join(loi))
    return redirect("thanh_toan:tien_chua_khop")
