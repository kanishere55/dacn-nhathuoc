from ung_dung.chung.permissions import kiem_tra_quyen

from .models import NhatKyEmail


def lay_nhat_ky_email(nguoi, *, loai_email="", trang_thai="", tim=""):
    kiem_tra_quyen(nguoi, "email.xem")
    cac_email = NhatKyEmail.objects.select_related("tai_khoan")
    if loai_email:
        cac_email = cac_email.filter(loai_email=loai_email)
    if trang_thai:
        cac_email = cac_email.filter(trang_thai=trang_thai)
    if tim:
        cac_email = cac_email.filter(email_nhan__icontains=tim.lower())
    return cac_email
