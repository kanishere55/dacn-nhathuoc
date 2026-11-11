from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.views.decorators.vary import vary_on_headers

from ung_dung.chung.permissions import yeu_cau_quyen

from .forms import LocBaoCaoForm
from .selectors import lay_bao_cao
from .xuat import xuat_excel


@yeu_cau_quyen("bao_cao.xem")
@require_GET
@vary_on_headers("HX-Request")
def tong_hop(request):
    # Chỉ coi là đã lọc khi URL có trường của bộ lọc; tham số lạ (?utm_source=…, ?v=…) không làm
    # trang báo "bộ lọc chưa hợp lệ" mà vẫn hiện báo cáo mặc định.
    du_lieu = request.GET.copy()
    du_lieu.pop("xuat", None)
    if not any(ten in du_lieu for ten in LocBaoCaoForm.base_fields):
        du_lieu = None
    form = LocBaoCaoForm(du_lieu, nguoi=request.user)
    tham_so = form.initial if not form.is_bound else form.cleaned_data if form.is_valid() else None
    bao_cao = lay_bao_cao(request.user, **tham_so) if tham_so is not None else None
    if bao_cao is not None and request.GET.get("xuat") == "xlsx":
        chi_nhanh = tham_so.get("chi_nhanh")
        du_lieu = xuat_excel(
            bao_cao,
            tu_ngay=tham_so["tu_ngay"],
            den_ngay=tham_so["den_ngay"],
            ten_chi_nhanh=chi_nhanh.ten_chi_nhanh if chi_nhanh else "toàn phạm vi",
        )
        phan_hoi = HttpResponse(
            du_lieu,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        phan_hoi["Content-Disposition"] = (
            f'attachment; filename="bao-cao-{tham_so["tu_ngay"]:%Y%m%d}-{tham_so["den_ngay"]:%Y%m%d}.xlsx"'
        )
        return phan_hoi
    tep = "bao_cao/tong_hop.html"
    if request.headers.get("HX-Request"):
        tep += "#ket_qua"
    return render(request, tep, {"form": form, "bao_cao": bao_cao})
