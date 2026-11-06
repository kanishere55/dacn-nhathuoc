import inspect

from django.conf import settings


def nhan_dien_trang(request):
    if not settings.DEBUG or not settings.HIEN_NHAN_DIEN_TRANG:
        return {}
    ket_qua = request.resolver_match
    if ket_qua is None:
        return {}
    ham = inspect.unwrap(ket_qua.func)
    tep = inspect.getsourcefile(ham)
    if tep:
        from pathlib import Path

        try:
            tep = Path(tep).resolve().relative_to(settings.BASE_DIR).as_posix()
        except ValueError:
            tep = ham.__module__.replace(".", "/") + ".py"
    return {"nhan_dien": {"url": ket_qua.view_name, "view": f"{tep} → {ham.__name__}"}}
