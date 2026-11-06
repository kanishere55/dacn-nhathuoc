import os
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.checks import Error, register
from django.db import models

DUOI_TEP_DU_LIEU = frozenset(
    {
        ".csv",
        ".tsv",
        ".xlsx",
        ".xls",
        ".json",
        ".sqlite3",
        ".db",
        ".pkl",
        ".joblib",
        ".parquet",
        ".ipynb",
        ".log",
    }
)
DUOI_TEP_ANH = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".webp",
        ".tif",
        ".tiff",
        ".svg",
        ".avif",
        ".ico",
        ".heic",
    }
)
THU_MUC_BO_QUA = frozenset({".venv", "staticfiles", "__pycache__", ".git"})
CAC_BACKEND_POSTGRESQL = frozenset(
    {"django.db.backends.postgresql", "django.contrib.gis.db.backends.postgis"}
)


def tim_tep_du_lieu(thu_muc_goc: Path) -> list[Path]:
    cac_tep = []
    for thu_muc_hien_tai, thu_muc_con, ten_tep in os.walk(thu_muc_goc, followlinks=False):
        thu_muc_con[:] = [ten for ten in thu_muc_con if ten not in THU_MUC_BO_QUA]
        for ten in ten_tep:
            duong_dan = Path(thu_muc_hien_tai) / ten
            tuong_doi = duong_dan.relative_to(thu_muc_goc)
            duoi_tep = duong_dan.suffix.lower()
            if duoi_tep in DUOI_TEP_DU_LIEU or (
                duoi_tep in DUOI_TEP_ANH and "static" not in tuong_doi.parts[:-1]
            ):
                cac_tep.append(tuong_doi)
    return sorted(cac_tep)


@register("luu_tru")
def kiem_tra_luu_tru(app_configs=None, **kwargs):
    cac_loi = []
    if not settings.DATABASES or "default" not in settings.DATABASES:
        cac_loi.append(Error("Phải cấu hình kết nối PostgreSQL mặc định.", id="luu_tru.E001"))
    for ten_ket_noi, cau_hinh in settings.DATABASES.items():
        if cau_hinh.get("ENGINE") not in CAC_BACKEND_POSTGRESQL:
            cac_loi.append(
                Error(
                    f"Kết nối {ten_ket_noi!r} phải dùng PostgreSQL/PostGIS; không dùng SQLite kể cả khi test.",
                    id="luu_tru.E001",
                )
            )
    if settings.SESSION_ENGINE != "django.contrib.sessions.backends.db":
        cac_loi.append(Error("Phiên đăng nhập phải lưu trong database.", id="luu_tru.E002"))
    if settings.is_overridden("MEDIA_ROOT"):
        cac_loi.append(
            Error(
                "Không khai báo MEDIA_ROOT; nội dung tệp tải lên phải lưu trong CSDL.",
                id="luu_tru.E003",
            )
        )
    cac_app = apps.get_app_configs() if app_configs is None else app_configs
    for cau_hinh_app in cac_app:
        for model in cau_hinh_app.get_models():
            for cot in model._meta.get_fields():
                if isinstance(cot, models.FileField):
                    cac_loi.append(
                        Error(
                            f"{model._meta.label}.{cot.name} dùng FileField/ImageField; phải lưu bytea khi có đặc tả tệp.",
                            id="luu_tru.E004",
                        )
                    )
    thu_muc_goc = Path(settings.BASE_DIR)
    if not thu_muc_goc.is_dir():
        cac_loi.append(Error("BASE_DIR không phải thư mục project hiện hữu.", id="luu_tru.E005"))
    else:
        for tep in tim_tep_du_lieu(thu_muc_goc):
            cac_loi.append(
                Error(
                    f"Tệp dữ liệu hoặc ảnh ngoài static không được ở project: {tep.as_posix()}",
                    id="luu_tru.E006",
                )
            )
    for ten_bo_ghi, cau_hinh in settings.LOGGING.get("handlers", {}).items():
        if "filename" in cau_hinh or "FileHandler" in cau_hinh.get("class", ""):
            cac_loi.append(
                Error(
                    f"Bộ ghi {ten_bo_ghi!r} ghi log ra tệp; hãy dùng console.",
                    id="luu_tru.E007",
                )
            )
    return cac_loi
