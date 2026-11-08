"""Giỏ hàng lưu trong session PostgreSQL; khóa dòng session khi sửa để hai tab không ghi đè."""

from contextlib import contextmanager

from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..gio_hang import KHOA_GIO, SO_LUONG_TOI_DA, SO_THUOC_TOI_DA


@contextmanager
def sua_gio(phien):
    if not phien.session_key:
        gio = {}
        yield gio
        if gio:
            phien[KHOA_GIO] = gio
        return

    with transaction.atomic():
        ban_ghi = (
            Session.objects.select_for_update()
            .filter(session_key=phien.session_key, expire_date__gt=timezone.now())
            .first()
        )
        if ban_ghi is None:
            raise ValidationError("Phiên đã hết hạn. Vui lòng tải lại trang.")
        du_lieu = ban_ghi.get_decoded()
        gio = du_lieu.get(KHOA_GIO, {})
        yield gio
        if gio:
            du_lieu[KHOA_GIO] = gio
        else:
            du_lieu.pop(KHOA_GIO, None)
        ban_ghi.session_data = phien.encode(du_lieu)
        ban_ghi.save(update_fields=["session_data"])

        # SessionMiddleware không cần ghi lại bản sao của phiên đã cập nhật.
        da_sua = phien.modified
        if gio:
            phien[KHOA_GIO] = gio
        else:
            phien.pop(KHOA_GIO, None)
        phien.modified = da_sua


def them_thuoc(phien, thuoc, so_luong):
    with sua_gio(phien) as gio:
        ma = str(thuoc.pk)
        if ma not in gio and len(gio) >= SO_THUOC_TOI_DA:
            raise ValidationError(f"Giỏ chứa tối đa {SO_THUOC_TOI_DA} loại thuốc.")
        tong = gio.get(ma, 0) + so_luong
        if tong > SO_LUONG_TOI_DA:
            raise ValidationError(f"Mỗi thuốc đặt tối đa {SO_LUONG_TOI_DA} đơn vị.")
        gio[ma] = tong


def sua_so_luong(phien, id_thuoc, so_luong):
    with sua_gio(phien) as gio:
        ma = str(id_thuoc)
        if ma not in gio:
            raise ValidationError("Thuốc này không còn trong giỏ.")
        if so_luong:
            gio[ma] = so_luong
        else:
            del gio[ma]


def xoa_cac_thuoc(phien, cac_id_thuoc):
    with sua_gio(phien) as gio:
        for ma in cac_id_thuoc:
            gio.pop(str(ma), None)
