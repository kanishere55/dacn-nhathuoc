from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ung_dung.chung.permissions import co_quyen, thay_toan_chuoi, yeu_cau_quyen

from ..loc import loc_lo_thuoc
from ..models import LoThuoc
from ..selectors import lay_lo_kem_ton
from ..services.lo_thuoc import doi_dieu_kien_ban


@yeu_cau_quyen("lo_thuoc.xem")
def danh_sach(request):
    return render(
        request,
        "kho/lo_thuoc.html",
        {
            **loc_lo_thuoc(request).ngu_canh(lay_lo_kem_ton(request.user)),
            "hom_nay": timezone.localdate(),
            "duoc_sua": co_quyen(request.user, "lo_thuoc.sua") and thay_toan_chuoi(request.user),
        },
    )


@yeu_cau_quyen("lo_thuoc.sua")
@require_POST
def doi_trang_thai(request, ma):
    lo = get_object_or_404(LoThuoc, pk=ma)
    doi_dieu_kien_ban(request.user, lo, request.POST.get("duoc_phep_ban") == "1")
    return redirect("kho:lo_thuoc_danh_sach")
