from django.db import models

# Tập ký tự cố định giúp Python và PostgreSQL cho cùng kết quả ở mọi locale.
MA_KHOANG_TRANG = (
    *range(0x0009, 0x000E),
    0x0020,
    0x0085,
    0x00A0,
    0x1680,
    *range(0x2000, 0x200B),
    0x2028,
    0x2029,
    0x202F,
    0x205F,
    0x3000,
    0x200B,
    0xFEFF,
)
MA_CAM_MOT_DONG = (*range(0x0001, 0x0020), *range(0x007F, 0x00A0), 0x2028, 0x2029)
KY_TU_KHOANG_TRANG = "".join(chr(ma) for ma in MA_KHOANG_TRANG)
KY_TU_CAM_MOT_DONG = frozenset(chr(ma) for ma in MA_CAM_MOT_DONG)


def cat_khoang_trang(van_ban: str) -> str:
    return van_ban.strip(KY_TU_KHOANG_TRANG)


def la_mot_dong(van_ban: str) -> bool:
    return not any(ky_tu in KY_TU_CAM_MOT_DONG for ky_tu in van_ban)


class KhongRong(models.Func):
    function = "public.khong_rong"
    arity = 1
    output_field = models.BooleanField()


class DaCatKhoangTrang(models.Func):
    function = "public.da_cat_khoang_trang"
    arity = 1
    output_field = models.BooleanField()


class LaMotDong(models.Func):
    function = "public.la_mot_dong"
    arity = 1
    output_field = models.BooleanField()
