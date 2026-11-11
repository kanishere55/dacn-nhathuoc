from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ung_dung.chung.duong_dan import quay_lai
from ung_dung.chung.permissions import co_quyen, thay_toan_chuoi, yeu_cau_quyen

from ..loc import loc_lo_thuoc
from ..models import LichSuDieuKienLo, LoThuoc
from ..selectors import lay_lo_kem_ton
from ..services.lo_thuoc import doi_dieu_kien_ban


@yeu_cau_quyen("lo_thuoc.xem")
def danh_sach(request):
    ngu_canh = loc_lo_thuoc(request).ngu_canh(
        lay_lo_kem_ton(request.user).prefetch_related(
            Prefetch(
                "cac_lich_su_dieu_kien",
                queryset=LichSuDieuKienLo.objects.select_related("nguoi_thuc_hien").order_by(
                    "-thoi_diem_tao", "-pk"
                ),
            )
        )
    )
    return render(
        request,
        "kho/lo_thuoc.html",
        {
            **ngu_canh,
            "hom_nay": timezone.localdate(),
            "duoc_sua": co_quyen(request.user, "lo_thuoc.sua") and thay_toan_chuoi(request.user),
        },
    )


@yeu_cau_quyen("lo_thuoc.sua")
@require_POST
def doi_trang_thai(request, ma):
    lo = get_object_or_404(LoThuoc, pk=ma)
    duoc_phep_ban = request.POST.get("duoc_phep_ban") == "1"
    try:
        _, don_can_xu_ly = doi_dieu_kien_ban(
            request.user,
            lo,
            duoc_phep_ban,
            request.POST.get("ly_do", ""),
            request.POST.get("so_van_ban_thu_hoi", ""),
        )
    except ValidationError as loi:
        messages.error(request, f"Chưa đổi được lô {lo.ma_lo_thuoc}: {' '.join(loi.messages)}")
    else:
        messages.success(
            request,
            f"Đã {'mở bán lại' if duoc_phep_ban else 'khóa bán'} lô {lo.ma_lo_thuoc} "
            f"của {lo.thuoc.ten_thuoc} ở mọi chi nhánh.",
        )
        if don_can_xu_ly:
            messages.warning(
                request,
                f"{len(don_can_xu_ly)} đơn chưa tìm được lô thay thế. "
                "Mở Cảnh báo kho để xem đơn và liên hệ khách.",
            )
    return quay_lai(request, "kho:lo_thuoc_danh_sach")
