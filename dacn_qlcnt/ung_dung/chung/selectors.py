"""Bảng điều khiển khu quản lý: hàng việc cần làm theo vai trò và chi nhánh, doanh thu toàn chuỗi.

Mỗi việc có số đếm, mức độ (gấp / cần chú ý / theo dõi) và đường dẫn tới đúng danh sách đã
lọc, để người dùng bấm là thấy đúng những mục vừa đếm. Mỗi việc chỉ tính khi tài khoản có
quyền xem danh sách tương ứng; dữ liệu giới hạn theo chi nhánh như các trang danh sách.
"""

from datetime import datetime, time, timedelta

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.urls import reverse
from django.utils import timezone

from ung_dung.ban_hang.selectors import lay_don
from ung_dung.danh_muc.selectors import lay_chi_nhanh
from ung_dung.du_bao.selectors import lay_ket_qua_moi_nhat
from ung_dung.kho.selectors import lay_canh_bao_ton_thap, lay_so_du, lo_theo_muc_canh_bao
from ung_dung.tro_chuyen.selectors import lay_phong_co_tin_moi
from ung_dung.webgis.selectors import lay_tuy_chon_ban_do_nhiet

from .permissions import co_quyen, co_vai_tro, la_quan_tri

SO_DONG_TOM_TAT = 5
SO_MUC_MOI_VIEC = 3
# Đơn đặt giữ còn dưới chừng này giờ là sắp hết hạn, cần gọi nhắc khách.
GIO_SAP_HET_GIU = 3
THU_TU_MUC = {"gap": 0, "chu_y": 1, "theo_doi": 2}
NHAN_MUC = {"gap": "Cần làm ngay", "chu_y": "Cần xử lý", "theo_doi": "Theo dõi"}


def _gio(thoi_diem):
    return timezone.localtime(thoi_diem).strftime("%H:%M %d/%m") if thoi_diem else ""


def _tien(so_tien):
    from .templatetags.dinh_dang import tien

    return tien(so_tien)


def _viec(ma, nhan, so, muc, url, mo_ta="", cac_muc=()):
    return {
        "ma": ma,
        "nhan": nhan,
        "so": so,
        "muc": muc if so else "xong",
        "nhan_muc": NHAN_MUC.get(muc, ""),
        "url": url,
        "mo_ta": mo_ta,
        "cac_muc": list(cac_muc),
    }


def _muc_don(don, phu):
    return {
        "ten": don.ma_don_hang,
        "url": reverse("ban_hang:don_hang_chi_tiet", args=[don.pk]),
        "phu": phu,
    }


def _viec_don_hang(nguoi):
    """Đơn đặt giữ: sắp hết hạn giữ (gọi nhắc khách) và tổng số đơn đang chờ khách đến nhận."""
    bay_gio = timezone.now()
    don = lay_don(nguoi)
    ds = reverse("ban_hang:don_hang_danh_sach")
    dang_giu = don.filter(trang_thai="dang_giu", thoi_diem_het_giu__gt=bay_gio)
    sap_het = dang_giu.filter(
        thoi_diem_het_giu__lte=bay_gio + timedelta(hours=GIO_SAP_HET_GIU)
    ).order_by("thoi_diem_het_giu", "pk")
    so_sap_het = sap_het.count()
    so_dang_giu = dang_giu.count()
    return [
        _viec(
            "don_giu_sap_het_han",
            f"Đơn đặt giữ hết hạn trong {GIO_SAP_HET_GIU} giờ",
            so_sap_het,
            "chu_y",
            f"{ds}?trang_thai=dang_giu",
            "Gọi nhắc khách tới nhận trước hạn; quá hạn hệ thống tự nhả hàng."
            if so_sap_het
            else "",
            [_muc_don(d, f"hạn {_gio(d.thoi_diem_het_giu)}") for d in sap_het[:SO_MUC_MOI_VIEC]],
        ),
        _viec(
            "don_dang_giu",
            "Đơn đặt giữ chờ khách đến nhận",
            so_dang_giu,
            "theo_doi",
            f"{ds}?trang_thai=dang_giu",
            "Soạn sẵn thuốc theo đơn để khách đến là giao ngay." if so_dang_giu else "",
            [
                _muc_don(d, f"hạn {_gio(d.thoi_diem_het_giu)}")
                for d in dang_giu.order_by("thoi_diem_het_giu", "pk")[:SO_MUC_MOI_VIEC]
            ],
        ),
    ]


def _viec_hoa_don(nguoi):
    from ung_dung.ban_hang.selectors import lay_yeu_cau_xuat_hoa_don

    cho = lay_yeu_cau_xuat_hoa_don(nguoi, trang_thai="cho_xu_ly").order_by("thoi_diem_tao", "pk")
    so = cho.count()
    cu_nhat = cho.first()
    return [
        _viec(
            "hoa_don_cho_xu_ly",
            "Yêu cầu hóa đơn công ty chờ xử lý",
            so,
            "chu_y",
            f"{reverse('ban_hang:xuat_hoa_don_danh_sach')}?trang_thai=cho_xu_ly",
            f"Yêu cầu cũ nhất gửi lúc {_gio(cu_nhat.thoi_diem_tao)}." if cu_nhat else "",
            [
                {
                    "ten": yc.ten_cong_ty,
                    "url": reverse("ban_hang:don_hang_chi_tiet", args=[yc.don_hang_id]),
                    "phu": f"đơn {yc.don_hang.ma_don_hang}",
                }
                for yc in cho[:SO_MUC_MOI_VIEC]
            ],
        )
    ]


def _viec_email(nguoi):
    from ung_dung.thong_bao.selectors import lay_nhat_ky_email
    from ung_dung.thong_bao.services import dieu_kien_can_gui_lai

    so = lay_nhat_ky_email(nguoi).filter(dieu_kien_can_gui_lai()).count()
    return [
        _viec(
            "email_loi",
            "Thư gửi khách bị lỗi",
            so,
            "gap",
            f"{reverse('thong_bao:nhat_ky_email')}?trang_thai=can_gui_lai",
            "Khách chưa nhận được thư. Xem nguyên nhân rồi bấm “Gửi lại”." if so else "",
        )
    ]


def _viec_kho(nguoi):
    so_du = lay_so_du(nguoi=nguoi)
    canh_bao = reverse("kho:canh_bao")
    dem = {
        muc: lo_theo_muc_canh_bao(so_du, muc).count()
        for muc in ("het_han", "duoi_7", "duoi_30", "khoa_ban")
    }
    ton_thap = lay_canh_bao_ton_thap(nguoi)
    return (
        [
            _viec(
                "lo_het_han",
                "Lô đã hết hạn còn tồn",
                dem["het_han"],
                "gap",
                f"{canh_bao}?muc=het_han",
                "Không được bán. Tách khỏi kệ và lập phiếu xuất hủy." if dem["het_han"] else "",
            ),
            _viec(
                "lo_duoi_7",
                "Lô hết hạn trong 7 ngày",
                dem["duoi_7"],
                "chu_y",
                f"{canh_bao}?muc=duoi_7",
                "Ưu tiên bán trước hoặc trả nhà cung cấp." if dem["duoi_7"] else "",
            ),
            _viec(
                "ton_thap",
                "Thuốc tồn dưới ngưỡng",
                len(ton_thap),
                "chu_y",
                f"{canh_bao}?muc=ton_thap",
                "Nhập thêm hoặc xin điều chuyển từ chi nhánh khác." if ton_thap else "",
            ),
            _viec(
                "lo_duoi_30",
                "Lô hết hạn trong 30 ngày",
                dem["duoi_30"],
                "theo_doi",
                f"{canh_bao}?muc=duoi_30",
            ),
            _viec(
                "lo_khoa_ban",
                "Lô đang khóa bán",
                dem["khoa_ban"],
                "theo_doi",
                f"{canh_bao}?muc=khoa_ban",
            ),
        ],
        dem,
        ton_thap,
    )


def lay_hang_viec(nguoi):
    """Việc cần làm của tài khoản, việc gấp lên đầu. Trả (các việc có số, các việc đã xong, đếm kho)."""
    cac_viec = []
    dem_kho, ton_thap = {}, []
    if co_quyen(nguoi, "don_hang.xem"):
        cac_viec += _viec_don_hang(nguoi)
    if co_quyen(nguoi, "hoa_don_cong_ty.xem"):
        cac_viec += _viec_hoa_don(nguoi)
    if co_quyen(nguoi, "email.xem"):
        cac_viec += _viec_email(nguoi)
    if co_quyen(nguoi, "ton_kho.xem"):
        viec_kho, dem_kho, ton_thap = _viec_kho(nguoi)
        cac_viec += viec_kho
    if co_quyen(nguoi, "tro_chuyen.dung"):
        so = lay_phong_co_tin_moi(nguoi).count()
        cac_viec.append(
            _viec(
                "tin_nhan",
                "Tin nhắn khách chờ trả lời",
                so,
                "chu_y",
                reverse("tro_chuyen:danh_sach"),
                "Khách đang chờ dược sĩ phản hồi." if so else "",
            )
        )
    co_viec = sorted(
        (v for v in cac_viec if v["so"]),
        key=lambda v: THU_TU_MUC[v["muc"]],
    )
    da_xong = [v for v in cac_viec if not v["so"]]
    return co_viec, da_xong, dem_kho, ton_thap


def _ranh_gioi_ngay(ngay):
    return timezone.make_aware(datetime.combine(ngay, time.min))


def lay_doanh_thu(nguoi):
    """Doanh thu bán (phiếu bán, sau ưu đãi thành viên) hôm nay, hôm qua, 7 ngày, tháng này:
    tổng phạm vi và từng chi nhánh, cùng cách tính với báo cáo doanh thu."""
    from ung_dung.ban_hang.models import ChiTietPhieuBan

    hom_nay = timezone.localdate()
    moc = {
        "hom_nay": _ranh_gioi_ngay(hom_nay),
        "hom_qua": _ranh_gioi_ngay(hom_nay - timedelta(days=1)),
        "bay_ngay": _ranh_gioi_ngay(hom_nay - timedelta(days=6)),
        "thang": _ranh_gioi_ngay(hom_nay.replace(day=1)),
    }
    cac_chi_nhanh = list(lay_chi_nhanh(nguoi))
    tien = ExpressionWrapper(
        F("so_luong") * F("don_gia") - F("giam_gia_phan_bo"), output_field=DecimalField()
    )
    thoi_diem = "phieu_ban__thoi_diem_tao"
    dong = ChiTietPhieuBan.objects.filter(
        phieu_ban__chi_nhanh__in=cac_chi_nhanh, **{f"{thoi_diem}__gte": min(moc.values())}
    )
    theo_chi_nhanh = {
        hang["phieu_ban__chi_nhanh"]: hang
        for hang in dong.order_by()
        .values("phieu_ban__chi_nhanh")
        .annotate(
            hom_nay=Sum(tien, filter=Q(**{f"{thoi_diem}__gte": moc["hom_nay"]}), default=0),
            hom_qua=Sum(
                tien,
                filter=Q(
                    **{f"{thoi_diem}__gte": moc["hom_qua"], f"{thoi_diem}__lt": moc["hom_nay"]}
                ),
                default=0,
            ),
            bay_ngay=Sum(tien, filter=Q(**{f"{thoi_diem}__gte": moc["bay_ngay"]}), default=0),
            thang=Sum(tien, filter=Q(**{f"{thoi_diem}__gte": moc["thang"]}), default=0),
            so_phieu=Count(
                "phieu_ban", distinct=True, filter=Q(**{f"{thoi_diem}__gte": moc["hom_nay"]})
            ),
        )
    }
    bao_cao = reverse("bao_cao:tong_hop")
    cac_dong = []
    for chi_nhanh in cac_chi_nhanh:
        so = theo_chi_nhanh.get(chi_nhanh.pk, {})
        hom_nay_cn, hom_qua_cn = so.get("hom_nay", 0), so.get("hom_qua", 0)
        cac_dong.append(
            {
                "chi_nhanh": chi_nhanh,
                "hom_nay": hom_nay_cn,
                "hom_qua": hom_qua_cn,
                "bay_ngay": so.get("bay_ngay", 0),
                "thang": so.get("thang", 0),
                "so_phieu": so.get("so_phieu", 0),
                "chenh_lech": (
                    round((hom_nay_cn - hom_qua_cn) / hom_qua_cn * 100) if hom_qua_cn else None
                ),
                "url": f"{bao_cao}?chi_nhanh={chi_nhanh.pk}"
                f"&tu_ngay={hom_nay.replace(day=1):%Y-%m-%d}&den_ngay={hom_nay:%Y-%m-%d}",
            }
        )
    cac_dong.sort(key=lambda d: d["thang"], reverse=True)
    tong = {
        ten: sum(d[ten] for d in cac_dong)
        for ten in ("hom_nay", "hom_qua", "bay_ngay", "thang", "so_phieu")
    }
    return {"tong": tong, "cac_chi_nhanh": cac_dong}


def lay_bang_dieu_khien(nguoi):
    # Mỗi khối dữ liệu chỉ nạp khi tài khoản có quyền xem tương ứng.
    quyen = {
        "duoc_xem_kho": co_quyen(nguoi, "ton_kho.xem"),
        "duoc_xem_don": co_quyen(nguoi, "don_hang.xem"),
        "duoc_ban": co_quyen(nguoi, "phieu_ban.tao"),
        "duoc_chat": co_quyen(nguoi, "tro_chuyen.dung"),
        "duoc_xem_bao_cao": co_quyen(nguoi, "bao_cao.xem"),
        "duoc_xem_du_bao": co_quyen(nguoi, "du_bao.xem"),
        "duoc_xem_ban_do_nhiet": co_quyen(nguoi, "ban_do_nhiet.xem"),
    }
    co_viec, da_xong, dem_kho, ton_thap = lay_hang_viec(nguoi)
    cac_lo = _lo_can_theo_doi(nguoi) if quyen["duoc_xem_kho"] else []
    don_cho_nhan = lay_don(nguoi).filter(con_hieu_luc=True).order_by("thoi_diem_het_giu", "pk")
    if not quyen["duoc_xem_don"]:
        don_cho_nhan = don_cho_nhan.none()
    noi_dung = {
        **quyen,
        "hom_nay": timezone.localdate(),
        "quan_tri_chuoi": la_quan_tri(nguoi),
        "quan_ly_chi_nhanh": co_vai_tro(nguoi, "quan_ly_chi_nhanh"),
        "cac_viec": co_viec,
        "cac_viec_da_xong": da_xong,
        "so_viec_gap": sum(1 for v in co_viec if v["muc"] == "gap"),
        "so_lo_het_han": dem_kho.get("het_han", 0),
        "so_lo_canh_bao": sum(dem_kho.values()),
        "so_canh_bao_ton_thap": len(ton_thap),
        "cac_lo_canh_bao": cac_lo,
        "cac_canh_bao_ton_thap": ton_thap[:SO_DONG_TOM_TAT],
        "so_don_cho_nhan": don_cho_nhan.count(),
        "cac_don_cho_nhan": list(don_cho_nhan[:SO_DONG_TOM_TAT]),
        "ban_hom_nay": _ban_hom_nay(nguoi) if co_quyen(nguoi, "phieu_ban.xem") else None,
    }
    if noi_dung["quan_tri_chuoi"]:
        du_bao = lay_ket_qua_moi_nhat()
        noi_dung.update(
            tieu_de="Tổng quan quản trị chuỗi",
            so_chi_nhanh=lay_chi_nhanh(nguoi, ca_chi_nhanh_ngung=True).count(),
            doanh_thu=lay_doanh_thu(nguoi) if quyen["duoc_xem_bao_cao"] else None,
            ban_do_nhiet=lay_tuy_chon_ban_do_nhiet(),
            lan_du_bao=du_bao["lan"],
            cac_nhom_du_bao=du_bao.get("cac_nhom", []),
        )
    else:
        cac_phong = (
            lay_phong_co_tin_moi(nguoi)
            if quyen["duoc_chat"]
            else lay_phong_co_tin_moi(nguoi).none()
        )
        noi_dung.update(
            tieu_de=(
                "Tổng quan quản lý chi nhánh"
                if noi_dung["quan_ly_chi_nhanh"]
                else "Tổng quan nhân viên"
            ),
            chi_nhanh=nguoi.chi_nhanh,
            so_cuoc_co_tin_moi=cac_phong.count(),
            cac_cuoc_co_tin_moi=list(cac_phong[:SO_DONG_TOM_TAT]),
        )
    return noi_dung


def _lo_can_theo_doi(nguoi):
    """Vài lô gấp nhất (hết hạn, sắp hết hạn trong 30 ngày, khóa bán) cho khối tóm tắt kho."""
    hom_nay = timezone.localdate()
    return list(
        lay_so_du(nguoi=nguoi)
        .filter(so_luong__gt=0)
        .filter(
            Q(lo_thuoc__ngay_het_han__lte=hom_nay + timedelta(days=30))
            | Q(lo_thuoc__duoc_phep_ban=False)
        )
        .select_related("lo_thuoc__thuoc", "chi_nhanh")
        .order_by("lo_thuoc__ngay_het_han", "pk")[:SO_DONG_TOM_TAT]
    )


def _ban_hom_nay(nguoi):
    """Số phiếu và doanh thu hàng hôm nay trong phạm vi, sau ưu đãi thành viên."""
    from ung_dung.ban_hang.models import ChiTietPhieuBan
    from ung_dung.ban_hang.selectors import lay_phieu_ban

    phieu = lay_phieu_ban(nguoi).filter(thoi_diem_tao__date=timezone.localdate())
    tien = ExpressionWrapper(
        F("so_luong") * F("don_gia") - F("giam_gia_phan_bo"), output_field=DecimalField()
    )
    return {
        "so_phieu": phieu.count(),
        "doanh_thu": ChiTietPhieuBan.objects.filter(phieu_ban__in=phieu).aggregate(
            tong=Sum(tien, default=0)
        )["tong"],
    }
