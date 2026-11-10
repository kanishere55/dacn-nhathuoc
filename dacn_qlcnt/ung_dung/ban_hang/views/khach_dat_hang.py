"""Trang đặt hàng: chọn nhận tại nhà thuốc hoặc giao tận nơi, chi nhánh, thanh toán."""

from django.conf import settings
from django.contrib import messages
from django.contrib.gis.db.models.functions import Distance
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.vary import vary_on_headers

from ung_dung.chung.permissions import yeu_cau_vai_tro
from ung_dung.danh_muc.selectors import lay_chi_nhanh_cong_khai
from ung_dung.kho.selectors import loc_chi_nhanh_du_thuoc
from ung_dung.tai_khoan.selectors import cac_dia_chi_cua
from ung_dung.thanh_toan.selectors import phuong_thuc_kha_dung

from ..forms import DatHangForm
from ..models import PHUONG_THUC_THANH_TOAN
from ..selectors import lay_dong_gio, lay_gio, tom_tat_gio
from ..services.dat_hang import dat_hang as tao_don
from ..services.giao_hang import BAN_KINH_GIAO_MET, phuong_an_giao
from ..services.gio_hang import sua_gio
from ..thanh_vien import giam_thanh_vien, hang_cua

PHUONG_THUC_GIAO = [muc for muc in PHUONG_THUC_THANH_TOAN if muc[0] != "tai_quay"]


def _phuong_an_tai_quay(cac_dong, dia_chi):
    cac_chi_nhanh = lay_chi_nhanh_cong_khai()
    if dia_chi:
        cac_chi_nhanh = cac_chi_nhanh.annotate(
            khoang_cach_thang=Distance("vi_tri", dia_chi.vi_tri)
        ).order_by("khoang_cach_thang")
    return [
        {
            "chi_nhanh": cn,
            "khoang_cach_met": getattr(getattr(cn, "khoang_cach_thang", None), "m", None),
        }
        for cn in loc_chi_nhanh_du_thuoc(list(cac_chi_nhanh), cac_dong)
    ]


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
    hinh_thuc = lua_chon.get("hinh_thuc_nhan") or (
        "nhan_tai_quay" if tom_tat["co_ke_don"] else "giao_hang"
    )
    if tom_tat["co_ke_don"]:
        hinh_thuc = "nhan_tai_quay"
    cac_dia_chi = list(cac_dia_chi_cua(request.user))
    dia_chi = next(
        (dc for dc in cac_dia_chi if dc.pk == lua_chon.get("dia_chi")),
        next(
            (dc for dc in cac_dia_chi if dc.pk == request.user.dia_chi_giao_hang_mac_dinh_id),
            cac_dia_chi[0] if cac_dia_chi else None,
        ),
    )
    if hinh_thuc == "giao_hang":
        cac_phuong_an = phuong_an_giao(dia_chi.vi_tri, cac_dong) if dia_chi else []
    else:
        cac_phuong_an = _phuong_an_tai_quay(cac_dong, dia_chi)
    phuong_an = next(
        (pa for pa in cac_phuong_an if pa["chi_nhanh"].pk == lua_chon.get("chi_nhanh")),
        cac_phuong_an[0] if cac_phuong_an else None,
    )
    kha_dung = phuong_thuc_kha_dung()
    phuong_thuc = "tai_quay"
    if hinh_thuc == "giao_hang":
        phuong_thuc = lua_chon.get("phuong_thuc_thanh_toan")
        phuong_thuc = phuong_thuc if phuong_thuc in kha_dung else "cod"
    phi = phuong_an["phi_giao_hang"] if hinh_thuc == "giao_hang" and phuong_an else 0
    hang = hang_cua(request.user)
    giam = giam_thanh_vien(
        hang["phan_tram"],
        [(d["thuoc"], d["so_luong"], d["thuoc"].don_gia) for d in cac_dong if d["thuoc"]],
    )

    # GET được tự gợi ý phương án thay thế; POST mà lựa chọn của khách không còn hợp lệ thì
    # không tự đổi rồi tạo đơn, phải báo để khách xem lại và xác nhận.
    cac_thay_doi = []
    if xac_nhan and form.is_valid():
        if lua_chon.get("hinh_thuc_nhan") and lua_chon["hinh_thuc_nhan"] != hinh_thuc:
            cac_thay_doi.append("Giỏ có thuốc kê đơn nên chỉ nhận được tại nhà thuốc.")
        if lua_chon.get("dia_chi") and (not dia_chi or dia_chi.pk != lua_chon["dia_chi"]):
            cac_thay_doi.append("Địa chỉ đã chọn không còn trong sổ địa chỉ.")
        if lua_chon.get("chi_nhanh") and (
            not phuong_an or phuong_an["chi_nhanh"].pk != lua_chon["chi_nhanh"]
        ):
            cac_thay_doi.append("Chi nhánh đã chọn không còn đáp ứng được đơn này.")
        if hinh_thuc == "giao_hang" and lua_chon.get("phuong_thuc_thanh_toan") not in (
            None,
            "",
            phuong_thuc,
        ):
            cac_thay_doi.append("Phương thức thanh toán đã chọn hiện không dùng được.")
        if cac_thay_doi:
            messages.warning(
                request,
                " ".join(cac_thay_doi)
                + " Hệ thống đã chọn phương án thay thế, hãy kiểm tra lại rồi bấm đặt hàng.",
            )

    if xac_nhan and form.is_valid() and phuong_an and not cac_thay_doi:
        giao = None
        if hinh_thuc == "giao_hang":
            giao = {
                "ten_nguoi_nhan": dia_chi.ten_nguoi_nhan,
                "so_dien_thoai": dia_chi.so_dien_thoai,
                "dia_chi": dia_chi.dia_chi
                + (f" (Ghi chú: {dia_chi.ghi_chu})" if dia_chi.ghi_chu else ""),
                "vi_tri": dia_chi.vi_tri,
                "khoang_cach_met": phuong_an["khoang_cach_met"],
            }
        gio_luc_tinh = dict(lay_gio(request.session))
        try:
            # Khóa dòng session: hai lần bấm đặt hàng cùng lúc chỉ tạo được một đơn.
            with sua_gio(request.session) as gio:
                if gio != gio_luc_tinh:
                    raise ValidationError(
                        "Giỏ hàng vừa thay đổi hoặc đã được đặt. Hãy kiểm tra lại."
                    )
                don = tao_don(
                    request.user,
                    phuong_an["chi_nhanh"],
                    [d for d in cac_dong if d["thuoc"]],
                    hinh_thuc_nhan=hinh_thuc,
                    phuong_thuc_thanh_toan=phuong_thuc,
                    giao=giao,
                    ghi_chu_khach=form.cleaned_data["ghi_chu_khach"],
                )
                gio.clear()
        except ValidationError as loi:
            messages.error(request, " ".join(loi.messages))
            if not lay_gio(request.session):
                return redirect("ban_hang:khach_don_hang_danh_sach")
        else:
            if don.trang_thai == "cho_thanh_toan":
                return redirect("thanh_toan:trang_thanh_toan", ma=don.pk)
            messages.success(request, f"Đặt đơn {don.ma_don_hang} thành công.")
            return redirect("ban_hang:khach_don_hang_chi_tiet", ma=don.pk)
    du_lieu_ban_do = {
        "hinh_thuc": hinh_thuc,
        "khach": (
            {"vi_do": dia_chi.vi_tri.y, "kinh_do": dia_chi.vi_tri.x, "dia_chi": dia_chi.dia_chi}
            if dia_chi
            else None
        ),
        "cac_chi_nhanh": [
            {
                "id": pa["chi_nhanh"].pk,
                "ten": pa["chi_nhanh"].ten_chi_nhanh,
                "dia_chi": pa["chi_nhanh"].dia_chi,
                "vi_do": pa["chi_nhanh"].vi_tri.y,
                "kinh_do": pa["chi_nhanh"].vi_tri.x,
                "chon": bool(phuong_an) and pa["chi_nhanh"].pk == phuong_an["chi_nhanh"].pk,
                "khoang_cach_met": pa.get("khoang_cach_met"),
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
            "hinh_thuc": hinh_thuc,
            "cac_dia_chi": cac_dia_chi,
            "dia_chi": dia_chi,
            "cac_phuong_an": cac_phuong_an,
            "phuong_an": phuong_an,
            "phuong_thuc": phuong_thuc,
            "cac_phuong_thuc_giao": PHUONG_THUC_GIAO,
            "phuong_thuc_kha_dung": kha_dung,
            "phi_giao_hang": phi,
            "tong_thanh_toan": tom_tat["tien_hang"] - giam + phi,
            "hang": hang,
            "giam_thanh_vien": giam,
            "ban_kinh_km": BAN_KINH_GIAO_MET // 1000,
        },
    )
    if cap_nhat_khoi:
        phan_hoi["X-Khoi-Dat-Hang"] = "lua-chon"
    return phan_hoi
