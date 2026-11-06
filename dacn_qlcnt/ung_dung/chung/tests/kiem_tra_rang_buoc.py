from collections.abc import Collection, Sequence
from typing import Any

from django.db import DatabaseError, transaction


class LoiBoKiemTra(AssertionError):
    """Lỗi cú pháp, kết nối hoặc khai báo ca thử không chứng minh được ràng buộc."""


class LoiCaKiemTra(AssertionError):
    """Dữ liệu được nhận/chặn khác với kết quả mong đợi của ca thử."""


def kiem_tra_ca_sai(
    con_tro: Any,
    cau_lenh: str,
    tham_so: Sequence[Any] | None,
    sqlstate_mong_doi: str,
    rang_buoc_mong_doi: str | Collection[str] | None,
) -> None:
    cac_ten = (
        {rang_buoc_mong_doi}
        if isinstance(rang_buoc_mong_doi, str) or rang_buoc_mong_doi is None
        else set(rang_buoc_mong_doi)
    )
    if not sqlstate_mong_doi.startswith(("22", "23")) or not cac_ten:
        raise LoiBoKiemTra("Ca sai phải khai báo SQLSTATE và tên ràng buộc mong đợi.")
    try:
        with transaction.atomic(using=con_tro.db.alias):
            con_tro.execute(cau_lenh, tham_so)
            raise LoiCaKiemTra("Dữ liệu sai vẫn được nhận; ca thử không đạt.")
    except DatabaseError as loi:
        loi_goc = loi.__cause__
        sqlstate = getattr(loi_goc, "sqlstate", None) or getattr(loi_goc, "pgcode", None)
        ten_rang_buoc = getattr(getattr(loi_goc, "diag", None), "constraint_name", None)
        if sqlstate != sqlstate_mong_doi:
            raise LoiBoKiemTra(
                f"SQLSTATE thực tế {sqlstate!r}, mong đợi {sqlstate_mong_doi!r}; "
                "không được tính lỗi SQL hoặc thiếu quyền là dữ liệu bị chặn đúng."
            ) from loi
        if ten_rang_buoc not in cac_ten:
            raise LoiCaKiemTra(
                f"Ràng buộc thực tế {ten_rang_buoc!r}, mong đợi {cac_ten!r}."
            ) from loi


def kiem_tra_ca_dung(
    con_tro: Any,
    cau_lenh: str,
    tham_so: Sequence[Any] | None = None,
) -> None:
    try:
        with transaction.atomic(using=con_tro.db.alias):
            con_tro.execute(cau_lenh, tham_so)
            so_dong = con_tro.rowcount
            lenh_thuc_te = con_tro.statusmessage.split(" ", 1)[0]
            if lenh_thuc_te not in {"INSERT", "UPDATE", "DELETE", "MERGE"} or so_dong < 1:
                raise LoiCaKiemTra("Ca đúng phải ghi được ít nhất một dòng.")
    except DatabaseError as loi:
        raise LoiCaKiemTra("Ca dữ liệu đúng lại bị từ chối.") from loi
