from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from ung_dung.chung.permissions import kiem_tra_quyen, thay_toan_chuoi
from ung_dung.chung.van_ban import cat_khoang_trang, la_mot_dong
from ung_dung.danh_muc.models import ChiNhanh

from ..models import LichSuDieuKienLo, LoThuoc


@transaction.atomic
def doi_dieu_kien_ban(nguoi, lo_thuoc, duoc_phep_ban, ly_do="", so_van_ban_thu_hoi=""):
    """Khóa hoặc mở bán một lô ở mọi chi nhánh và ghi nhật ký (người, lúc, lý do, văn bản).

    Khóa bán bắt buộc có lý do (nghi lỗi, chờ kiểm nghiệm, thu hồi...) để người xử lý sau
    biết vì sao lô bị biệt trữ (GPP: biệt trữ thuốc thu hồi chờ xử lý).
    """
    # Cờ bán nằm ở lô dùng chung của mọi chi nhánh nên cần thêm phạm vi toàn chuỗi.
    kiem_tra_quyen(nguoi, "lo_thuoc.sua")
    if not thay_toan_chuoi(nguoi):
        raise PermissionDenied("Đổi điều kiện bán của lô cần phạm vi toàn chuỗi.")
    ly_do = cat_khoang_trang(ly_do or "").replace("\r\n", "\n")
    so_van_ban_thu_hoi = cat_khoang_trang(so_van_ban_thu_hoi or "")
    if not duoc_phep_ban and not ly_do:
        raise ValidationError(
            {"ly_do": "Hãy ghi lý do khóa bán, ví dụ: nghi hàng lỗi, chờ kiểm nghiệm, thu hồi."}
        )
    if not la_mot_dong(so_van_ban_thu_hoi):
        raise ValidationError({"so_van_ban_thu_hoi": "Số văn bản chỉ ghi trên một dòng."})
    # Dùng cùng thứ tự khóa như điều chuyển trước khi đổi tính hợp lệ toàn chuỗi.
    list(ChiNhanh.objects.select_for_update().order_by("pk").values_list("pk", flat=True))
    lo = LoThuoc.objects.select_for_update().get(pk=lo_thuoc.pk)
    if lo.duoc_phep_ban == duoc_phep_ban:
        # Bấm hai lần hoặc hai người cùng thao tác: không ghi thêm dòng nhật ký trùng.
        return lo, []
    lo.duoc_phep_ban = duoc_phep_ban
    lo.save(update_fields=["duoc_phep_ban"])
    lich_su = LichSuDieuKienLo(
        lo_thuoc=lo,
        duoc_phep_ban=duoc_phep_ban,
        ly_do=ly_do,
        so_van_ban_thu_hoi=so_van_ban_thu_hoi,
        nguoi_thuc_hien=nguoi,
    )
    lich_su.full_clean()
    lich_su.save()
    if duoc_phep_ban:
        return lo, []
    from ung_dung.ban_hang.services.giu_hang import phan_bo_lai_giu_cua_lo

    return lo, phan_bo_lai_giu_cua_lo(lo)
