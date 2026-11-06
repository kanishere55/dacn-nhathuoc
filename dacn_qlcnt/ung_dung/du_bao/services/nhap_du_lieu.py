from hashlib import sha256
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from thuc_nghiem_du_bao.du_lieu import CAC_NHOM_ATC
from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import NguonDuLieu, QuanSatBanHang


def doc_salesdaily(duong_dan):
    tep = Path(duong_dan).resolve(strict=True)
    if (
        tep.is_relative_to(settings.BASE_DIR.resolve())
        or not tep.is_file()
        or tep.suffix.lower() != ".csv"
    ):
        raise ValidationError("Chọn salesdaily.csv nằm ngoài thư mục project.")
    if tep.stat().st_size > 10 * 1024 * 1024:
        raise ValidationError("Tệp nguồn vượt giới hạn 10 MiB.")
    noi_dung = tep.read_bytes()
    try:
        bang = pd.read_csv(BytesIO(noi_dung), usecols=["datum", *CAC_NHOM_ATC])
        bang["datum"] = pd.to_datetime(bang["datum"], format="%m/%d/%Y", errors="raise")
        bang = bang.sort_values("datum").set_index("datum")
        bang = bang[list(CAC_NHOM_ATC)].apply(pd.to_numeric, errors="raise")
    except (ValueError, TypeError) as loi:
        raise ValidationError("CSV phải có ngày dạng tháng/ngày/năm và đủ tám cột ATC.") from loi
    if (
        len(bang) < 100
        or bang.index.hasnans
        or bang.index.min().year != 2014
        or bang.index.max().year != 2019
        or not bang.index.equals(pd.date_range(bang.index.min(), bang.index.max(), freq="D"))
    ):
        raise ValidationError("Nguồn phải có chuỗi ngày liên tục, không trùng, từ 2014 đến 2019.")
    luong = bang.to_numpy(dtype=float)
    if not np.isfinite(luong).all() or (luong < 0).any():
        raise ValidationError("Lượng bán phải hữu hạn và không âm ở mỗi ngày/ATC.")
    return bang, sha256(noi_dung).hexdigest()


@transaction.atomic
def nap_salesdaily(duong_dan, ten_nguon):
    bang, ma_bam = doc_salesdaily(duong_dan)
    nguon, da_tao = NguonDuLieu.objects.get_or_create(
        bam_sha256=ma_bam,
        defaults={
            "ten_nguon_du_lieu": cat_khoang_trang(ten_nguon),
            "don_vi_nguon": "Lượng bán theo đơn vị gốc Pharma Sales Data",
        },
    )
    if da_tao:
        QuanSatBanHang.objects.bulk_create(
            [
                QuanSatBanHang(
                    nguon_du_lieu=nguon,
                    ma_atc_nguon=nhom,
                    ngay_ban=ngay.date(),
                    so_luong=float(luong),
                )
                for nhom in CAC_NHOM_ATC
                for ngay, luong in bang[nhom].items()
            ],
            batch_size=1000,
        )
    return nguon, da_tao
