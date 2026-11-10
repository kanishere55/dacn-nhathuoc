from django.db import transaction

from ung_dung.chung.permissions import kiem_tra_quyen

from ..models import KichBanThieuHang


@transaction.atomic
def tao_kich_ban(nguoi, du_bao, **so_lieu):
    kiem_tra_quyen(nguoi, "du_bao.chay")
    kich_ban = KichBanThieuHang(du_bao_bay_ngay=du_bao, **so_lieu)
    kich_ban.full_clean()
    kich_ban.save()
    return kich_ban
