import inspect
from pathlib import Path

from django.conf import settings


def nhan_dien_trang(request):
    if not settings.DEBUG or not settings.HIEN_NHAN_DIEN_TRANG:
        return {}
    ket_qua = request.resolver_match
    if ket_qua is None:
        return {}
    ham = ket_qua.func
    doi_tuong = getattr(ham, "view_class", None) or getattr(ham, "cls", None)
    if doi_tuong is None:
        doi_tuong = inspect.unwrap(ham)
    tep = inspect.getsourcefile(doi_tuong)
    if tep:
        try:
            tep = Path(tep).resolve().relative_to(settings.BASE_DIR).as_posix()
        except ValueError:
            tep = doi_tuong.__module__.replace(".", "/") + ".py"
    return {"nhan_dien": {"url": ket_qua.view_name, "view": f"{tep} → {doi_tuong.__name__}"}}
