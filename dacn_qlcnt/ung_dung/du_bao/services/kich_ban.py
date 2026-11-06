from django.db import transaction

from ung_dung.chung.permissions import kiem_tra_vai_tro

from ..models import KichBanThieuHang


@transaction.atomic
def tao_kich_ban(nguoi, du_bao, **so_lieu):
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
    kich_ban = KichBanThieuHang(du_bao_bay_ngay=du_bao, **so_lieu)
    kich_ban.full_clean()
    kich_ban.save()
    return kich_ban
