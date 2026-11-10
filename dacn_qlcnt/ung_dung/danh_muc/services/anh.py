from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max

from ung_dung.chung.permissions import kiem_tra_quyen, thay_toan_chuoi

from ..models import AnhNoiDung
from ..selectors import CO_ANH

SO_ANH_TOI_DA = 8


def _kiem_tra_pham_vi(nguoi, loai, doi_tuong):
    """Quyền `chi_nhanh.sua` không có phạm vi toàn chuỗi chỉ sửa ảnh chi nhánh của mình."""
    kiem_tra_quyen(nguoi, f"{loai}.sua")
    if loai == "chi_nhanh" and not thay_toan_chuoi(nguoi) and nguoi.chi_nhanh_id != doi_tuong.pk:
        raise PermissionDenied("Chi nhánh không thuộc phạm vi của bạn.")


@transaction.atomic
def them_anh(nguoi, loai, doi_tuong, cac_tep):
    _kiem_tra_pham_vi(nguoi, loai, doi_tuong)
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
    _kiem_tra_pham_vi(nguoi, loai, doi_tuong)
    # Khóa đối tượng cha trước, cùng thứ tự với mọi thao tác trên bộ ảnh, để không khóa chéo.
    CO_ANH[loai][0].objects.select_for_update().get(pk=doi_tuong.pk)
    _lay_anh(loai, doi_tuong, id_anh).delete()


@transaction.atomic
def dat_anh_dai_dien(nguoi, loai, doi_tuong, id_anh):
    """Đưa ảnh lên đầu bộ ảnh; các ảnh khác giữ nguyên thứ tự tương đối."""
    _kiem_tra_pham_vi(nguoi, loai, doi_tuong)
    model_chu, model_anh, ten_khoa = CO_ANH[loai]
    model_chu.objects.select_for_update().get(pk=doi_tuong.pk)
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


QUYEN_TAI_ANH_NOI_DUNG = (
    "thuoc.sua",
    "chi_nhanh.sua",
    "tin_tuc.sua",
    "trang.sua",
    "banner.sua",
    "thong_tin.sua",
)


@transaction.atomic
def luu_anh_noi_dung(nguoi, tep):
    """Lưu ảnh chèn trong trình soạn thảo; trả bản ghi để lấy id đưa vào đường dẫn ảnh."""
    kiem_tra_quyen(nguoi, *QUYEN_TAI_ANH_NOI_DUNG)
    anh = AnhNoiDung(tai_khoan=nguoi)
    anh.gan_du_lieu(tep)
    anh.save()
    return anh
