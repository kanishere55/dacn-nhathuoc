"""Trang đặt giữ: chọn chi nhánh còn đủ toàn bộ thuốc trong giỏ rồi xác nhận giữ hàng 24 giờ."""

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.vary import vary_on_headers

from ung_dung.chung.permissions import yeu_cau_vai_tro
from ung_dung.danh_muc.selectors import du_lieu_ban_do_chi_nhanh, lay_chi_nhanh_cong_khai
from ung_dung.kho.selectors import loc_chi_nhanh_du_thuoc
from ung_dung.webgis.services.duong_di import quang_duong_tu_vi_tri

from ..forms import DatHangForm
from ..selectors import lay_dong_gio, lay_gio, tom_tat_gio
from ..services.dat_hang import GIO_GIU_TAI_QUAY
from ..services.dat_hang import dat_hang as tao_don
from ..services.gio_hang import sua_gio
from ..thanh_vien import giam_thanh_vien, hang_cua


def _cac_chi_nhanh_du_hang(cac_dong, vi_tri):
    """Chi nhánh còn đủ toàn bộ giỏ trên lô còn hạn tới hết thời gian giữ.

    Có vị trí của khách thì PostGIS sắp sơ bộ (ST_Distance), OSRM cho quãng đường đi thực tế;
    danh sách sắp theo quãng đường đó, gần nhất trước.
    """
    cac_chi_nhanh = lay_chi_nhanh_cong_khai()
    if vi_tri:
        cac_chi_nhanh = cac_chi_nhanh.annotate(khoang_cach=Distance("vi_tri", vi_tri)).order_by(
            "khoang_cach"
        )
    du_hang = loc_chi_nhanh_du_thuoc(
        list(cac_chi_nhanh),
        cac_dong,
        con_han_den=timezone.localdate(timezone.now() + timedelta(hours=GIO_GIU_TAI_QUAY)),
    )
    if not vi_tri:
        return [{"chi_nhanh": cn, "quang_duong": None} for cn in du_hang]
    quang_duong = quang_duong_tu_vi_tri(
        vi_tri, [(cn.pk, cn.vi_tri, cn.khoang_cach.m) for cn in du_hang]
    )
    return sorted(
        ({"chi_nhanh": cn, "quang_duong": quang_duong[cn.pk]} for cn in du_hang),
        key=lambda pa: pa["quang_duong"]["quang_duong_met"],
    )


@yeu_cau_vai_tro("khach_hang")
@require_http_methods(["GET", "POST"])
@never_cache
@vary_on_headers("HX-Request")
def dat_hang(request):
    cap_nhat_khoi = request.method == "GET" and request.headers.get("HX-Request") == "true"
    xac_nhan = request.method == "POST" and "cap_nhat" not in request.POST
    cac_dong = lay_dong_gio(lay_gio(request.session))
    tom_tat = tom_tat_gio(cac_dong)
    if not tom_tat["hop_le"]:
        messages.error(request, "Giỏ hàng trống hoặc có thuốc đã ngừng kinh doanh.")
        if cap_nhat_khoi:
            return HttpResponse(headers={"HX-Redirect": reverse("ban_hang:gio_hang")})
        return redirect("ban_hang:gio_hang")
    du_lieu = request.POST if request.method == "POST" else request.GET
    form = DatHangForm(du_lieu or None)
    form.is_valid()
    lua_chon = form.cleaned_data if form.is_bound else {}
    vi_tri = None
    if lua_chon.get("vi_do") is not None and lua_chon.get("kinh_do") is not None:
        vi_tri = Point(lua_chon["kinh_do"], lua_chon["vi_do"], srid=4326)
    nhan_vi_tri = (lua_chon.get("nhan_vi_tri") or "vị trí hiện tại của bạn") if vi_tri else ""
    cac_phuong_an = _cac_chi_nhanh_du_hang(cac_dong, vi_tri)
    phuong_an = next(
        (pa for pa in cac_phuong_an if pa["chi_nhanh"].pk == lua_chon.get("chi_nhanh")),
        cac_phuong_an[0] if cac_phuong_an else None,
    )
    hang = hang_cua(request.user)
    giam = giam_thanh_vien(
        hang["phan_tram"],
        [(d["thuoc"], d["so_luong"], d["thuoc"].don_gia) for d in cac_dong if d["thuoc"]],
    )

    # GET được tự gợi ý chi nhánh khác; POST mà chi nhánh khách chọn không còn đủ hàng thì
    # không tự đổi rồi tạo đơn, phải báo để khách xem lại và xác nhận.
    doi_chi_nhanh = bool(
        xac_nhan
        and form.is_valid()
        and lua_chon.get("chi_nhanh")
        and (not phuong_an or phuong_an["chi_nhanh"].pk != lua_chon["chi_nhanh"])
    )
    if doi_chi_nhanh:
        messages.warning(
            request,
            "Chi nhánh đã chọn không còn đủ hàng cho đơn này. Hệ thống đã gợi ý chi nhánh khác, "
            "hãy kiểm tra lại rồi bấm đặt giữ.",
        )

    if xac_nhan and form.is_valid() and phuong_an and not doi_chi_nhanh:
        gio_luc_tinh = dict(lay_gio(request.session))
        try:
            # Khóa dòng session: hai lần bấm đặt giữ cùng lúc chỉ tạo được một đơn.
            with sua_gio(request.session) as gio:
                if gio != gio_luc_tinh:
                    raise ValidationError(
                        "Giỏ hàng vừa thay đổi hoặc đã được đặt. Hãy kiểm tra lại."
                    )
                don = tao_don(
                    request.user,
                    phuong_an["chi_nhanh"],
                    [d for d in cac_dong if d["thuoc"]],
                    ghi_chu_khach=form.cleaned_data["ghi_chu_khach"],
                    tong_khach_xac_nhan=form.cleaned_data["tong_da_xem"],
                )
                gio.clear()
        except ValidationError as loi:
            messages.error(request, " ".join(loi.messages))
            if not lay_gio(request.session):
                return redirect("ban_hang:khach_don_hang_danh_sach")
        else:
            messages.success(
                request,
                f"Đã giữ hàng cho đơn {don.ma_don_hang} tại {don.chi_nhanh.ten_chi_nhanh} đến "
                f"{timezone.localtime(don.thoi_diem_het_giu):%H:%M %d/%m}.",
            )
            return redirect("ban_hang:khach_don_hang_chi_tiet", ma=don.pk)
    du_lieu_ban_do = {
        "khach": (
            {"vi_do": vi_tri.y, "kinh_do": vi_tri.x, "dia_chi": "Bạn ở đây"} if vi_tri else None
        ),
        "cac_chi_nhanh": [
            {
                **du_lieu_ban_do_chi_nhanh(pa["chi_nhanh"], pa["quang_duong"]),
                "chon": bool(phuong_an) and pa["chi_nhanh"].pk == phuong_an["chi_nhanh"].pk,
            }
            for pa in cac_phuong_an
        ],
        "osrm": settings.OSRM_BASE_URL,
    }
    ten_tep = "ban_hang/khach/dat_hang.html"
    if cap_nhat_khoi:
        ten_tep += "#lua_chon"
    phan_hoi = render(
        request,
        ten_tep,
        {
            "du_lieu_ban_do": du_lieu_ban_do,
            "form": form,
            "cac_dong": cac_dong,
            "tom_tat": tom_tat,
            "vi_tri": vi_tri,
            "nhan_vi_tri": nhan_vi_tri,
            "cac_phuong_an": cac_phuong_an,
            "phuong_an": phuong_an,
            "tong_thanh_toan": tom_tat["tien_hang"] - giam,
            "hang": hang,
            "giam_thanh_vien": giam,
            "gio_giu": GIO_GIU_TAI_QUAY,
            "het_giu_du_kien": timezone.now() + timedelta(hours=GIO_GIU_TAI_QUAY),
        },
    )
    if cap_nhat_khoi:
        phan_hoi["X-Khoi-Dat-Hang"] = "lua-chon"
    return phan_hoi
