from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count, OuterRef, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.vary import vary_on_headers

from ung_dung.chung.permissions import co_quyen

from ..forms import NHAN, TaiAnhForm, lay_form
from ..loc import tao_bo_loc
from ..selectors import CO_ANH, DANH_MUC, lay_danh_muc
from ..services.danh_muc import luu_danh_muc


def _hien_gia_tri(gia_tri):
    if gia_tri is None or gia_tri == "":
        return "—"
    if isinstance(gia_tri, bool):
        return "Có" if gia_tri else "Không"
    if isinstance(gia_tri, Decimal):
        return f"{gia_tri:,.0f}".replace(",", ".") + " ₫"
    if isinstance(gia_tri, date):
        return f"{gia_tri:%d/%m/%Y}"
    return gia_tri


@vary_on_headers("HX-Request")
def hien_danh_sach(request, loai):
    model, tieu_de, cac_cot = DANH_MUC[loai]
    tap_hop = lay_danh_muc(request.user, loai)
    cac_khoa_ngoai = [
        cot for cot in cac_cot if getattr(model._meta.get_field(cot), "is_relation", False)
    ]
    if cac_khoa_ngoai:
        tap_hop = tap_hop.select_related(*cac_khoa_ngoai)
    co_anh = loai in CO_ANH
    if co_anh:
        _, model_anh, ten_khoa = CO_ANH[loai]
        anh_dau = model_anh.objects.filter(**{ten_khoa: OuterRef("pk")}).order_by("thu_tu", "pk")
        tap_hop = tap_hop.annotate(
            id_anh_dai_dien=Subquery(anh_dau.values("pk")[:1]),
            so_anh=Count("cac_anh", distinct=True),
        )
    loc = tao_bo_loc(request, loai)
    ngu_canh = loc.ngu_canh(tap_hop)
    cac_dong = [
        {
            "ma": doi_tuong.pk,
            "o": [_hien_gia_tri(getattr(doi_tuong, cot)) for cot in cac_cot],
            "id_anh": getattr(doi_tuong, "id_anh_dai_dien", None),
            "so_anh": getattr(doi_tuong, "so_anh", 0),
            "ten": str(doi_tuong),
        }
        for doi_tuong in ngu_canh["trang"]
    ]
    return render(
        request,
        "danh_muc/danh_sach.html",
        {
            **ngu_canh,
            "tieu_de": tieu_de,
            "loai": loai,
            "cac_cot": [NHAN.get(cot, cot) for cot in cac_cot],
            "cac_dong": cac_dong,
            "co_anh": co_anh,
            "duoc_sua": co_quyen(request.user, f"{loai}.sua"),
        },
    )


def hien_form(request, loai, ma=None):
    doi_tuong = get_object_or_404(lay_danh_muc(request.user, loai), pk=ma) if ma else None
    form = lay_form(loai)(request.POST or None, instance=doi_tuong)
    if request.method == "POST" and form.is_valid():
        try:
            da_luu = luu_danh_muc(request.user, loai, form.cleaned_data, doi_tuong)
        except ValidationError as loi:
            form.add_error(None, loi)
        except IntegrityError:
            form.add_error(None, "Mã trùng hoặc dữ liệu đã được thay đổi.")
        else:
            if not doi_tuong and loai in CO_ANH:
                messages.success(request, "Đã tạo. Hãy thêm ảnh cho mục này ở phần bên dưới.")
                return redirect(f"danh_muc:{loai}_sua", ma=da_luu.pk)
            return redirect(f"danh_muc:{loai}_danh_sach")
    ngu_canh = {"form": form, "tieu_de": DANH_MUC[loai][1], "loai": loai, "doi_tuong": doi_tuong}
    if doi_tuong and loai in CO_ANH:
        _, model_anh, ten_khoa = CO_ANH[loai]
        ngu_canh["cac_anh"] = model_anh.objects.filter(**{ten_khoa: doi_tuong}).defer(
            "noi_dung_anh"
        )
        ngu_canh["form_anh"] = TaiAnhForm()
    return render(request, "danh_muc/form.html", ngu_canh)
