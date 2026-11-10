from django.core.exceptions import PermissionDenied
from django.db import transaction

from ung_dung.chung.permissions import kiem_tra_quyen, thay_toan_chuoi
from ung_dung.danh_muc.models import ChiNhanh

from ..models import LoThuoc


@transaction.atomic
def doi_dieu_kien_ban(nguoi, lo_thuoc, duoc_phep_ban):
    # Cờ bán nằm ở lô dùng chung của mọi chi nhánh nên cần thêm phạm vi toàn chuỗi.
    kiem_tra_quyen(nguoi, "lo_thuoc.sua")
    if not thay_toan_chuoi(nguoi):
        raise PermissionDenied("Đổi điều kiện bán của lô cần phạm vi toàn chuỗi.")
    # Dùng cùng thứ tự khóa như điều chuyển trước khi đổi tính hợp lệ toàn chuỗi.
    list(ChiNhanh.objects.select_for_update().order_by("pk").values_list("pk", flat=True))
    lo = LoThuoc.objects.select_for_update().get(pk=lo_thuoc.pk)
    lo.duoc_phep_ban = duoc_phep_ban
    lo.save(update_fields=["duoc_phep_ban"])
    return lo
