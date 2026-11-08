from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max

from ung_dung.chung.permissions import kiem_tra_vai_tro

from ..selectors import CO_ANH

SO_ANH_TOI_DA = 8


@transaction.atomic
def them_anh(nguoi, loai, doi_tuong, cac_tep):
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
    model_chu, model_anh, ten_khoa = CO_ANH[loai]
    chu = model_chu.objects.select_for_update().get(pk=doi_tuong.pk)
    hien_co = model_anh.objects.filter(**{ten_khoa: chu})
    if hien_co.count() + len(cac_tep) > SO_ANH_TOI_DA:
        raise ValidationError(f"Mỗi mục chỉ lưu tối đa {SO_ANH_TOI_DA} ảnh.")
    thu_tu = (hien_co.aggregate(lon_nhat=Max("thu_tu"))["lon_nhat"] or 0) + 1
    cac_anh = []
    for so, tep in enumerate(cac_tep):
        anh = model_anh(**{ten_khoa: chu}, thu_tu=thu_tu + so)
        anh.gan_du_lieu(tep)
        anh.save()
        cac_anh.append(anh)
    return cac_anh


def _lay_anh(loai, doi_tuong, id_anh):
    _, model_anh, ten_khoa = CO_ANH[loai]
    anh = model_anh.objects.select_for_update().filter(pk=id_anh, **{ten_khoa: doi_tuong}).first()
    if anh is None:
        raise ValidationError("Ảnh không thuộc mục này.")
    return anh


@transaction.atomic
def xoa_anh(nguoi, loai, doi_tuong, id_anh):
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
    _lay_anh(loai, doi_tuong, id_anh).delete()


@transaction.atomic
def dat_anh_dai_dien(nguoi, loai, doi_tuong, id_anh):
    """Đưa ảnh lên đầu bộ ảnh; các ảnh khác giữ nguyên thứ tự tương đối."""
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
    _, model_anh, ten_khoa = CO_ANH[loai]
    anh = _lay_anh(loai, doi_tuong, id_anh)
    cac_anh = list(
        model_anh.objects.select_for_update()
        .filter(**{ten_khoa: doi_tuong})
        .exclude(pk=anh.pk)
        .order_by("thu_tu", "pk")
        .defer("noi_dung_anh")
    )
    for so, khac in enumerate([anh, *cac_anh]):
        model_anh.objects.filter(pk=khac.pk).update(thu_tu=so)
