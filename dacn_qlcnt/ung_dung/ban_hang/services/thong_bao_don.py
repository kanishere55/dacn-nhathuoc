"""Email gửi khách theo từng sự kiện của đơn: đặt đơn, đổi trạng thái, nhận tiền, chờ hoàn tiền,
đã hoàn tiền, trả hàng và hóa đơn công ty.

Mỗi thư nói rõ khách cần làm gì tiếp theo, kèm hạn bằng giờ tuyệt đối và nút đi thẳng tới
đúng trang (thanh toán, chỉ đường, đơn, hóa đơn). Nội dung dựng ở đây; trình bày nằm trong
thong_bao/templates/thong_bao/email/. Thư chỉ gửi khi khách có email.
"""

from django.utils import timezone

from ung_dung.chung.templatetags.dinh_dang import tien
from ung_dung.thong_bao.services import gui_email, url_tuyet_doi

from .trang_thai import NHAN

# Màu nhãn trạng thái trùng trang web (static/css/don_hang.css): (nền, chữ).
MAU_NHAN = {
    "cho": ("#fff4dc", "#8a5a00"),
    "dang": ("#e4f0fb", "#1d5a8f"),
    "xong": ("#e3f3e9", "#136b48"),
    "huy": ("#fdecec", "#9f2a22"),
    "trung_tinh": ("#eef1ef", "#45524b"),
}
NHOM_MAU = {
    "cho_thanh_toan": "cho",
    "cho_xac_nhan": "cho",
    "dang_giu": "dang",
    "dang_chuan_bi": "dang",
    "dang_giao": "dang",
    "hoan_thanh": "xong",
    "da_huy": "huy",
    "giao_that_bai": "huy",
    "het_han": "trung_tinh",
}
# Các bước trên dòng tiến trình, giống trang chi tiết đơn của khách.
BUOC = {
    "giao_hang": ["cho_xac_nhan", "dang_chuan_bi", "dang_giao", "hoan_thanh"],
    "nhan_tai_quay": ["dang_giu", "hoan_thanh"],
}
# Tiền tố nội bộ hệ thống thêm vào mã tham chiếu; khách chỉ cần phần mã gốc.
TIEN_TO_MA = ("sepay-", "momo-", "tay-", "hoan-", "tra-")


def _gio(thoi_diem):
    return timezone.localtime(thoi_diem).strftime("%H:%M %d/%m/%Y") if thoi_diem else ""


def _tien(so_tien):
    return tien(so_tien).replace(" ", " ")


def ma_hien_thi(ma_tham_chieu):
    """Mã giao dịch khách đối chiếu được với ngân hàng/ví (bỏ tiền tố nội bộ)."""
    ma = ma_tham_chieu or ""
    for tien_to in TIEN_TO_MA:
        if ma.startswith(tien_to):
            return ma[len(tien_to) :]
    return ma


def tien_trinh(don):
    """[(nhãn, đã qua, hiện tại)] cho dòng tiến trình; rỗng khi đơn đã kết thúc bất thường."""
    cac_buoc = BUOC[don.hinh_thuc_nhan]
    if don.trang_thai == "cho_thanh_toan":
        cac_buoc = ["cho_thanh_toan", *cac_buoc]
    if don.trang_thai not in cac_buoc:
        return []
    vi_tri = cac_buoc.index(don.trang_thai)
    return [(NHAN[buoc], so <= vi_tri, so == vi_tri) for so, buoc in enumerate(cac_buoc)]


def _the(nhan, nhom, tieu_de, mo_ta="", *, ma_nhan="Mã đơn", ma_gia_tri="", thoi_diem=None):
    nen, chu = MAU_NHAN[nhom]
    return {
        "nhan": nhan,
        "nen": nen,
        "chu": chu,
        "tieu_de": tieu_de,
        "mo_ta": mo_ta,
        "ma_nhan": ma_nhan,
        "ma_gia_tri": ma_gia_tri,
        "thoi_diem": thoi_diem or timezone.now(),
        "canh_bao": "",
    }


def _nut(nhan, url):
    return {"nhan": nhan, "url": url}


def _ten_khach(don):
    return don.khach_hang.ho_ten or don.khach_hang.ten_dang_nhap


def _dien_thoai_lien_he(don):
    """Số gọi khi cần hỗ trợ đơn: điện thoại chi nhánh, không có thì hotline chung."""
    from ung_dung.noi_dung.selectors import thong_tin_cua_hang

    return don.chi_nhanh.so_dien_thoai or thong_tin_cua_hang().hotline


def _cau_lien_he(don):
    so = _dien_thoai_lien_he(don)
    return f"Cần hỗ trợ, gọi {so} hoặc trả lời thư này." if so else "Cần hỗ trợ, trả lời thư này."


def _lich_su_moi_nhat(don):
    return (
        don.cac_lich_su.select_related("nguoi_thuc_hien").order_by("-thoi_diem_tao", "-pk").first()
    )


def _giao_dich(don, loai):
    from ung_dung.thanh_toan.models import GiaoDichThanhToan

    return (
        GiaoDichThanhToan.objects.filter(don_hang=don, loai_giao_dich=loai, trang_thai="thanh_cong")
        .order_by("-pk")
        .first()
    )


def _doi_soat(don):
    """Phải thu, đã thu, còn thiếu, phải hoàn của đơn: một nguồn chung với nghiệp vụ thanh toán."""
    from ung_dung.thanh_toan.services.doi_soat import doi_soat

    return doi_soat(don)


def _dong_giao_dich(giao_dich, nhan_so_tien):
    dong = [
        (nhan_so_tien, _tien(giao_dich.so_tien)),
        ("Kênh", giao_dich.get_phuong_thuc_display()),
    ]
    if giao_dich.ma_tham_chieu:
        dong.append(("Mã giao dịch", ma_hien_thi(giao_dich.ma_tham_chieu)))
    dong.append(("Thời điểm", _gio(giao_dich.thoi_diem_hoan_tat or giao_dich.thoi_diem_tao)))
    return dong


def _ngu_canh_don(don):
    cac_dong = list(don.cac_dong.select_related("thuoc__don_vi_tinh").order_by("pk"))
    buoc = tien_trinh(don)
    return {
        "don": don,
        "cac_dong": cac_dong,
        "co_ke_don": any(dong.thuoc.la_thuoc_ke_don for dong in cac_dong),
        "loi_chao": f"Xin chào {_ten_khach(don)},",
        "url_don": url_tuyet_doi("ban_hang:khach_don_hang_chi_tiet", don.pk),
        "url_chi_nhanh": url_tuyet_doi(
            "danh_muc:khach_chi_nhanh_chi_tiet", don.chi_nhanh.ma_chi_nhanh
        ),
        "tien_trinh": buoc,
        "buoc_hien_tai": next((so + 1 for so, (_, _, hien_tai) in enumerate(buoc) if hien_tai), 0),
        "do_rong_buoc": f"{100 // len(buoc)}%" if buoc else "",
        "hien_nhan_hang": True,
        "hien_san_pham": True,
        "cac_luu_y": [],
        "ghi_chu": "",
    }


def _gui_thu_don(don, *, loai_email, tieu_de, mau, ngu_canh, dinh_kem_hoa_don=False):
    the = ngu_canh["the"]
    gui_email(
        loai_email=loai_email,
        email_nhan=don.khach_hang.email,
        tai_khoan=don.khach_hang,
        don_hang=don,
        dinh_kem_hoa_don=dinh_kem_hoa_don,
        tieu_de=tieu_de,
        tom_tat=" ".join(filter(None, [the["tieu_de"] + ".", the["mo_ta"]]))[:150],
        mau=mau,
        ngu_canh=ngu_canh,
    )


# Đặt đơn và đổi trạng thái


def _noi_dung_theo_trang_thai(don, ghi_chu="", *, phieu=None):
    """Ngữ cảnh thư theo trạng thái hiện tại của đơn và tiêu đề thư tương ứng.

    `phieu`: phiếu bán của đơn hoàn thành; có thì thư kèm hóa đơn PDF và nút tải hóa đơn.
    """
    nc = _ngu_canh_don(don)
    ma, tong = don.ma_don_hang, _tien(don.tong_thanh_toan)
    nhan = NHAN[don.trang_thai]
    nhom = NHOM_MAU[don.trang_thai]
    nut_don = _nut("Xem đơn", nc["url_don"])
    luu_y = nc["cac_luu_y"]
    lich_su = _lich_su_moi_nhat(don)
    tt = don.trang_thai

    if tt == "cho_thanh_toan":
        the = _the(
            nhan,
            nhom,
            f"Thanh toán trước {_gio(don.thoi_diem_het_giu)} để giữ đơn",
            f"Đơn {tong} thanh toán qua {don.get_phuong_thuc_thanh_toan_display()}. Hàng được "
            f"giữ cho bạn đến {_gio(don.thoi_diem_het_giu)}; quá hạn mà nhà thuốc chưa nhận "
            "được tiền thì đơn tự hủy.",
            ma_gia_tri=ma,
            thoi_diem=don.thoi_diem_tao,
        )
        if don.phuong_thuc_thanh_toan == "chuyen_khoan":
            luu_y.append(
                f"Chuyển đúng {tong} và ghi mã đơn {ma} trong nội dung để hệ thống tự xác nhận."
            )
        nc["nut_chinh"] = _nut(
            "Thanh toán ngay", url_tuyet_doi("thanh_toan:trang_thanh_toan", don.pk)
        )
        nc["nut_phu"] = nut_don
        tieu_de = f"Thanh toán đơn {ma} trước {timezone.localtime(don.thoi_diem_het_giu):%H:%M}"
    elif tt == "cho_xac_nhan":
        the = _the(
            "Đã nhận đơn",
            nhom,
            "Nhà thuốc đã nhận đơn của bạn",
            f"Dược sĩ sẽ xác nhận đơn trước {_gio(don.thoi_diem_het_giu)}. Quá hạn này mà chưa "
            "được xác nhận, đơn tự hủy và bạn không mất phí.",
            ma_gia_tri=ma,
            thoi_diem=don.thoi_diem_tao,
        )
        if don.phuong_thuc_thanh_toan == "cod":
            luu_y.append(f"Bạn trả {tong} cho người giao khi nhận hàng.")
        nc["nut_chinh"] = _nut("Theo dõi đơn", nc["url_don"])
        tieu_de = f"Đã nhận đơn {ma}"
    elif tt == "dang_giu":
        the = _the(
            nhan,
            nhom,
            f"Hàng được giữ đến {_gio(don.thoi_diem_het_giu)}",
            f"Đến {don.chi_nhanh.ten_chi_nhanh} trước thời điểm này, đọc mã đơn cho nhân viên "
            f"và thanh toán {tong} tại quầy.",
            ma_gia_tri=ma,
            thoi_diem=don.thoi_diem_tao,
        )
        if nc["co_ke_don"]:
            the["canh_bao"] = (
                "Đơn có thuốc kê đơn: mang theo đơn thuốc còn hạn của bác sĩ. Thiếu đơn thuốc, "
                "nhà thuốc không được bán."
            )
        luu_y.append("Đổi ý thì hủy ngay trong trang đơn để nhà thuốc nhả hàng cho người khác.")
        nc["nut_chinh"] = _nut("Xem đường đến nhà thuốc", nc["url_chi_nhanh"])
        nc["nut_phu"] = nut_don
        tieu_de = f"Đơn {ma} đang được giữ tại quầy"
    elif tt == "dang_chuan_bi":
        the = _the(
            nhan,
            nhom,
            "Dược sĩ đang soạn thuốc cho đơn của bạn",
            "Nhà thuốc sẽ báo tiếp khi đơn được giao cho người vận chuyển.",
            ma_gia_tri=ma,
        )
        if don.phuong_thuc_thanh_toan == "cod":
            luu_y.append(f"Chuẩn bị {tong} để trả khi nhận hàng.")
        nc["nut_chinh"] = _nut("Theo dõi đơn", nc["url_don"])
        tieu_de = f"Đơn {ma} đang được chuẩn bị"
    elif tt == "dang_giao":
        the = _the(
            nhan,
            nhom,
            "Đơn đang trên đường tới bạn",
            f"Người giao sẽ gọi số {don.so_dien_thoai_nhan} khi tới nơi.",
            ma_gia_tri=ma,
        )
        if don.phuong_thuc_thanh_toan == "cod":
            luu_y.append(f"Chuẩn bị {tong} để trả người giao.")
        luu_y.append("Khi nhận đủ thuốc, mở trang đơn và bấm “Đã nhận được hàng”.")
        nc["nut_chinh"] = _nut("Tôi đã nhận được hàng", nc["url_don"])
        tieu_de = f"Đơn {ma} đang được giao"
    elif tt == "hoan_thanh":
        from .tra_hang import han_tra_hang

        co_phieu = phieu is not None
        the = _the(
            nhan,
            nhom,
            "Đơn đã hoàn tất, cảm ơn bạn",
            "Bạn có thể mở hoặc tải hóa đơn bán lẻ từ nút bên dưới." if co_phieu else "",
            ma_gia_tri=ma,
        )
        han = han_tra_hang(don)
        if han:
            luu_y.append(
                "Thuốc có vấn đề do nhà thuốc (giao sai, hư hỏng, cận hạn)? Gửi yêu cầu trả hàng "
                f"trong trang đơn trước {_gio(han)}."
            )
        nc["han_tra_hang"] = han
        if lich_su and lich_su.nguoi_thuc_hien_id is None and not ghi_chu:
            ghi_chu = lich_su.ghi_chu
        if co_phieu:
            nc["nut_chinh"] = _nut(
                "Tải hóa đơn PDF", url_tuyet_doi("ban_hang:khach_hoa_don_pdf", don.pk)
            )
            nc["nut_phu"] = nut_don
        else:
            nc["nut_chinh"] = nut_don
        tieu_de = f"Đơn {ma} đã hoàn tất"
    elif tt == "da_huy":
        ai = getattr(lich_su, "nguoi_thuc_hien", None)
        if ai is None:
            mo_ta = "Hệ thống đã tự hủy đơn này."
        elif ai.vai_tro == "khach_hang":
            mo_ta = "Bạn đã hủy đơn này."
        else:
            mo_ta = "Nhà thuốc đã hủy đơn này."
        the = _the(nhan, nhom, "Đơn đã bị hủy", mo_ta, ma_gia_tri=ma)
        nc["nhan_ghi_chu"] = "Lý do"
        nc["nut_chinh"] = nut_don
        tieu_de = f"Đơn {ma} đã bị hủy"
    elif tt == "het_han":
        the = _the(
            nhan,
            nhom,
            "Đơn giữ tại quầy đã hết hạn",
            f"Đơn không được nhận trước {_gio(don.thoi_diem_het_giu)} nên hàng đã được trả lại "
            "kệ. Vẫn cần thuốc, bạn đặt đơn mới trên website.",
            ma_gia_tri=ma,
        )
        nc["nhan_ghi_chu"] = "Lý do"
        nc["nut_chinh"] = nut_don
        tieu_de = f"Đơn {ma} đã hết hạn giữ"
    else:  # giao_that_bai
        the = _the(
            nhan,
            nhom,
            "Giao hàng không thành công",
            "Đơn đã kết thúc và thuốc được chuyển về nhà thuốc. Vẫn cần thuốc, bạn đặt đơn mới "
            "hoặc gọi nhà thuốc để được hỗ trợ.",
            ma_gia_tri=ma,
        )
        nc["nhan_ghi_chu"] = "Lý do"
        nc["nut_chinh"] = nut_don
        tieu_de = f"Đơn {ma} giao không thành công"

    if don.trang_thai_thanh_toan == "cho_hoan_tien":
        luu_y.append(
            f"Nhà thuốc sẽ hoàn lại {_tien(_doi_soat(don).phai_hoan)} bạn đã thanh toán và gửi "
            "email kèm mã giao dịch khi hoàn xong."
        )
    if tt in ("da_huy", "het_han", "giao_that_bai", "cho_xac_nhan", "dang_chuan_bi"):
        luu_y.append(_cau_lien_he(don))
    nc.update(the=the, ghi_chu=ghi_chu)
    return tieu_de, nc


def bao_don_moi(don):
    if not don.khach_hang.email:
        return
    tieu_de, nc = _noi_dung_theo_trang_thai(don)
    _gui_thu_don(don, loai_email="don_hang_moi", tieu_de=tieu_de, mau="don_hang_moi", ngu_canh=nc)


def _vua_nhan_du_tien(don):
    """Đơn vừa chuyển chờ thanh toán → chờ xác nhận vì đã nhận đủ tiền."""
    lich_su = _lich_su_moi_nhat(don)
    return (
        don.trang_thai == "cho_xac_nhan"
        and don.trang_thai_thanh_toan == "da_thanh_toan"
        and lich_su is not None
        and lich_su.tu_trang_thai == "cho_thanh_toan"
    )


def bao_doi_trang_thai(don, ghi_chu=""):
    """Thư khi đơn đổi trạng thái; `ghi_chu` là lý do (hủy, giao thất bại) gửi nguyên văn cho khách.

    Hai trường hợp được chuyển sang thư riêng để khách đọc đúng việc vừa xảy ra:
    đã nhận đủ tiền (đơn sang chờ xác nhận) và đã hoàn tiền. Chỗ ghi hoàn tiền hiện gọi hàm
    này với ghi chú "Đã hoàn …" (trạng thái đơn không đổi); khi chỗ đó gọi thẳng
    bao_hoan_tien thì nhánh này không còn được dùng.
    """
    if not don.khach_hang.email:
        return
    if ghi_chu.startswith("Đã hoàn"):
        giao_dich = _giao_dich(don, "hoan")
        if giao_dich is not None:
            bao_hoan_tien(don, giao_dich)
            return
    if _vua_nhan_du_tien(don):
        bao_da_nhan_tien(don)
        return
    from ..hoa_don import ten_tep_pdf
    from ..models import PhieuBan

    phieu = (
        PhieuBan.objects.filter(don_hang=don).first() if don.trang_thai == "hoan_thanh" else None
    )
    tieu_de, nc = _noi_dung_theo_trang_thai(don, ghi_chu, phieu=phieu)
    if phieu is not None:
        nc["ten_tep_hoa_don"] = ten_tep_pdf(phieu)
        tieu_de = f"Đơn {don.ma_don_hang} đã hoàn tất – xem hóa đơn"
    _gui_thu_don(
        don,
        loai_email="don_hang_cap_nhat",
        tieu_de=tieu_de,
        mau="don_hang_cap_nhat",
        ngu_canh=nc,
        dinh_kem_hoa_don=phieu is not None,
    )


def tep_hoa_don(id_don_hang):
    """(tên tệp, nội dung PDF, kiểu) của hóa đơn bán lẻ; dựng lúc gửi thư, sau commit."""
    from ..hoa_don import du_lieu_hoa_don, ten_tep_pdf, ve_pdf
    from ..models import PhieuBan

    phieu = PhieuBan.objects.filter(don_hang_id=id_don_hang).first()
    if phieu is None:
        return None
    return ten_tep_pdf(phieu), ve_pdf(du_lieu_hoa_don(phieu)), "application/pdf"


# Thanh toán và hoàn tiền


def bao_da_nhan_tien(don, giao_dich=None):
    """Thư "đã nhận tiền": đủ tiền, nhận thiếu (còn thiếu bao nhiêu, hạn bổ sung), nhận thừa,
    hoặc tiền tới khi đơn đã hủy (sẽ hoàn lại).

    `giao_dich`: dòng GiaoDichThanhToan thu vừa ghi; bỏ trống thì lấy khoản thu mới nhất.
    """
    if not don.khach_hang.email:
        return
    giao_dich = giao_dich or _giao_dich(don, "thu")
    nc = _ngu_canh_don(don)
    ma, tong = don.ma_don_hang, don.tong_thanh_toan
    doi_soat = _doi_soat(don)
    da_thu = doi_soat.da_thu
    luu_y = nc["cac_luu_y"]
    if don.trang_thai in ("da_huy", "het_han", "giao_that_bai"):
        the = _the(
            "Sẽ hoàn tiền",
            "huy",
            "Nhà thuốc đã nhận tiền nhưng đơn đã kết thúc",
            f"Đơn {ma} đã {NHAN[don.trang_thai].lower()} trước khi tiền tới nên nhà thuốc sẽ hoàn "
            "lại khoản này và gửi email kèm mã giao dịch khi hoàn xong.",
            ma_gia_tri=ma,
        )
        tieu_de = f"Đã nhận tiền cho đơn {ma} – sẽ hoàn lại"
        nc["hien_san_pham"] = False
    elif don.trang_thai == "cho_thanh_toan" and doi_soat.con_thieu > 0:
        con_thieu = _tien(doi_soat.con_thieu)
        the = _the(
            "Còn thiếu tiền",
            "cho",
            f"Còn thiếu {con_thieu} để hoàn tất thanh toán",
            f"Nhà thuốc đã nhận {_tien(da_thu)}, đơn cần {_tien(tong)}. Chuyển thêm {con_thieu} "
            f"trước {_gio(don.thoi_diem_het_giu)} và ghi mã đơn {ma} trong nội dung.",
            ma_gia_tri=ma,
        )
        luu_y.append("Quá hạn mà chưa đủ tiền, đơn tự hủy và số tiền bạn đã chuyển được hoàn lại.")
        nc["nut_chinh"] = _nut(
            "Thanh toán phần còn thiếu", url_tuyet_doi("thanh_toan:trang_thanh_toan", don.pk)
        )
        tieu_de = f"Đơn {ma}: còn thiếu {con_thieu}"
    else:
        the = _the(
            "Đã thanh toán",
            "xong",
            "Nhà thuốc đã nhận tiền thanh toán",
            (
                f"Đơn chuyển sang chờ dược sĩ xác nhận, hạn xác nhận {_gio(don.thoi_diem_het_giu)}."
                if don.trang_thai == "cho_xac_nhan"
                else f"Đơn hiện ở trạng thái “{NHAN[don.trang_thai]}”."
            ),
            ma_gia_tri=ma,
        )
        if doi_soat.phai_hoan > 0:
            luu_y.append(
                f"Bạn đã chuyển thừa {_tien(doi_soat.phai_hoan)}. Nhà thuốc sẽ hoàn lại phần thừa "
                "và báo qua email."
            )
        tieu_de = f"Đã nhận thanh toán đơn {ma}"
    nc["nut_chinh"] = nc.get("nut_chinh") or _nut("Theo dõi đơn", nc["url_don"])
    luu_y.append(_cau_lien_he(don))
    if giao_dich is not None:
        nc["tieu_de_thong_tin"] = "Khoản tiền vừa nhận"
        nc["cac_dong_thong_tin"] = _dong_giao_dich(giao_dich, "Số tiền")
        if da_thu != giao_dich.so_tien:
            nc["cac_dong_thong_tin"].append(("Tổng đã nhận cho đơn", _tien(da_thu)))
    nc["the"] = the
    _gui_thu_don(don, loai_email="da_nhan_tien", tieu_de=tieu_de, mau="da_nhan_tien", ngu_canh=nc)


def bao_hoan_tien(don, giao_dich):
    """Thư "đã hoàn tiền" riêng (không dùng thư đổi trạng thái): số tiền, kênh, mã giao dịch."""
    if not don.khach_hang.email:
        return
    nc = _ngu_canh_don(don)
    tien_mat = giao_dich.phuong_thuc == "tien_mat"
    nc.update(
        the=_the(
            "Đã hoàn tiền",
            "xong",
            f"Đã hoàn {_tien(giao_dich.so_tien)} cho bạn",
            "Bạn đã nhận lại tiền mặt tại nhà thuốc."
            if tien_mat
            else f"Nhà thuốc đã chuyển tiền hoàn qua {giao_dich.get_phuong_thuc_display().lower()}. "
            "Nếu chưa thấy tiền về, liên hệ nhà thuốc kèm mã giao dịch bên dưới để đối chiếu.",
            ma_gia_tri=don.ma_don_hang,
        ),
        hien_san_pham=False,
        hien_nhan_hang=False,
        tieu_de_thong_tin="Khoản đã hoàn",
        cac_dong_thong_tin=_dong_giao_dich(giao_dich, "Số tiền hoàn"),
        cac_luu_y=[_cau_lien_he(don)],
        nut_chinh=_nut("Xem đơn", url_tuyet_doi("ban_hang:khach_don_hang_chi_tiet", don.pk)),
    )
    _gui_thu_don(
        don,
        loai_email="hoan_tien",
        tieu_de=f"Đã hoàn {_tien(giao_dich.so_tien)} cho đơn {don.ma_don_hang}",
        mau="hoan_tien",
        ngu_canh=nc,
    )


# Trả hàng

LOI_NHAN_TRA_HANG = {
    "cho_duyet": (
        "Đã nhận yêu cầu",
        "cho",
        "Nhà thuốc đã nhận yêu cầu trả hàng",
        "Nhà thuốc sẽ liên hệ hẹn nhận lại hàng để kiểm tra. Giữ nguyên bao bì và hóa đơn nhé.",
    ),
    "da_duyet": (
        "Đã chấp nhận",
        "dang",
        "Yêu cầu trả hàng đã được chấp nhận",
        "Nhà thuốc đã nhận lại và kiểm hàng. Tiền hoàn sẽ được trả theo hình thức bạn chọn.",
    ),
    "tu_choi": (
        "Không chấp nhận",
        "huy",
        "Yêu cầu trả hàng chưa được chấp nhận",
        "Nhà thuốc đã kiểm tra và chưa thể nhận trả hàng cho yêu cầu này.",
    ),
    "da_hoan_tien": (
        "Đã hoàn tiền",
        "xong",
        "Đã hoàn tiền cho yêu cầu trả hàng",
        "Nhà thuốc đã hoàn tiền cho các thuốc bạn trả lại.",
    ),
}
TIEU_DE_TRA_HANG = {
    "cho_duyet": "Đã nhận yêu cầu trả hàng {ma}",
    "da_duyet": "Yêu cầu trả hàng {ma} được chấp nhận",
    "tu_choi": "Yêu cầu trả hàng {ma} chưa được chấp nhận",
    "da_hoan_tien": "Đã hoàn tiền yêu cầu trả hàng {ma}",
}


def _giao_dich_tra_hang(yeu_cau):
    from ung_dung.thanh_toan.models import GiaoDichThanhToan

    return (
        GiaoDichThanhToan.objects.filter(
            don_hang_id=yeu_cau.don_hang_id,
            loai_giao_dich="hoan",
            trang_thai="thanh_cong",
            ghi_chu__contains=yeu_cau.ma_yeu_cau_tra_hang,
        )
        .order_by("-pk")
        .first()
    )


def bao_tra_hang(yeu_cau):
    don = yeu_cau.don_hang
    if not don.khach_hang.email:
        return
    nhan, nhom, tieu_de_lon, mo_ta = LOI_NHAN_TRA_HANG[yeu_cau.trang_thai]
    nc = _ngu_canh_don(don)
    dong = [("Đơn hàng", don.ma_don_hang), ("Lý do trả", yeu_cau.get_ly_do_display())]
    if yeu_cau.trang_thai != "tu_choi":
        dong.append(("Số tiền hoàn", _tien(yeu_cau.so_tien_hoan)))
        dong.append(("Hình thức nhận tiền", yeu_cau.get_hinh_thuc_hoan_tien_display()))
    luu_y = []
    if yeu_cau.trang_thai == "da_duyet" and yeu_cau.hinh_thuc_hoan_tien == "tai_quay":
        luu_y.append(
            f"Mang mã yêu cầu {yeu_cau.ma_yeu_cau_tra_hang} tới {don.chi_nhanh.ten_chi_nhanh} "
            f"({don.chi_nhanh.dia_chi}) để nhận tiền mặt."
        )
    if yeu_cau.trang_thai == "da_hoan_tien":
        giao_dich = _giao_dich_tra_hang(yeu_cau)
        if giao_dich is not None:
            dong = [d for d in dong if d[0] not in ("Số tiền hoàn", "Hình thức nhận tiền")]
            dong += _dong_giao_dich(giao_dich, "Số tiền hoàn")
            if giao_dich.phuong_thuc != "tien_mat":
                luu_y.append(
                    "Nếu chưa thấy tiền về, liên hệ nhà thuốc kèm mã giao dịch để đối chiếu."
                )
    luu_y.append(_cau_lien_he(don))
    nc.update(
        the=_the(
            nhan,
            nhom,
            tieu_de_lon,
            mo_ta,
            ma_nhan="Mã yêu cầu",
            ma_gia_tri=yeu_cau.ma_yeu_cau_tra_hang,
            thoi_diem=yeu_cau.thoi_diem_xu_ly or yeu_cau.thoi_diem_tao,
        ),
        tien_trinh=[],
        hien_san_pham=False,
        hien_nhan_hang=False,
        ghi_chu=yeu_cau.ghi_chu_xu_ly,
        nhan_ghi_chu="Lý do" if yeu_cau.trang_thai == "tu_choi" else "Ghi chú của nhà thuốc",
        cac_dong_tra=list(yeu_cau.cac_dong.select_related("chi_tiet_don_hang__thuoc__don_vi_tinh")),
        tieu_de_thong_tin="Thông tin yêu cầu",
        cac_dong_thong_tin=dong,
        cac_luu_y=luu_y,
        nut_chinh=_nut("Xem đơn", nc["url_don"]),
    )
    _gui_thu_don(
        don,
        loai_email="tra_hang",
        tieu_de=TIEU_DE_TRA_HANG[yeu_cau.trang_thai].format(ma=yeu_cau.ma_yeu_cau_tra_hang),
        mau="tra_hang",
        ngu_canh=nc,
    )


# Hóa đơn công ty


def _dong_cong_ty(yeu_cau):
    return [
        ("Công ty", yeu_cau.ten_cong_ty),
        ("Mã số thuế", yeu_cau.ma_so_thue),
        ("Địa chỉ", yeu_cau.dia_chi_cong_ty),
        ("Email nhận hóa đơn", yeu_cau.email_nhan_hoa_don),
        ("Đơn hàng", yeu_cau.don_hang.ma_don_hang),
    ]


def _ngu_canh_hoa_don(yeu_cau, the):
    nc = _ngu_canh_don(yeu_cau.don_hang)
    nc.update(
        the=the,
        tien_trinh=[],
        hien_san_pham=False,
        hien_nhan_hang=False,
        tieu_de_thong_tin="Thông tin xuất hóa đơn",
        cac_dong_thong_tin=_dong_cong_ty(yeu_cau),
    )
    return nc


def bao_da_nhan_yeu_cau_hoa_don(yeu_cau):
    """Thư xác nhận khách vừa gửi yêu cầu hóa đơn công ty (gửi chủ tài khoản)."""
    don = yeu_cau.don_hang
    if not don.khach_hang.email:
        return
    nc = _ngu_canh_hoa_don(
        yeu_cau,
        _the(
            "Chờ xử lý",
            "cho",
            "Nhà thuốc đã nhận yêu cầu hóa đơn công ty",
            "Nhân viên sẽ phát hành hóa đơn điện tử trên phần mềm hóa đơn của nhà thuốc rồi báo "
            "kết quả qua email này. Hóa đơn điện tử được gửi tới email nhận hóa đơn bên dưới.",
            ma_gia_tri=don.ma_don_hang,
            thoi_diem=yeu_cau.thoi_diem_tao,
        ),
    )
    nc["cac_luu_y"] = [_cau_lien_he(don)]
    nc["nut_chinh"] = _nut("Xem đơn", nc["url_don"])
    _gui_thu_don(
        don,
        loai_email="xuat_hoa_don",
        tieu_de=f"Đã nhận yêu cầu hóa đơn công ty – đơn {don.ma_don_hang}",
        mau="xuat_hoa_don",
        ngu_canh=nc,
    )


def bao_ket_qua_hoa_don(yeu_cau):
    """Kết quả yêu cầu hóa đơn công ty: gửi chủ tài khoản; khi đã xuất mà email nhận hóa đơn
    khác email tài khoản thì gửi thêm bản trung tính cho kế toán (không chào tên khách, không
    có nút cần đăng nhập)."""
    don = yeu_cau.don_hang
    da_xuat = yeu_cau.trang_thai == "da_xuat"
    if da_xuat:
        the = _the(
            "Đã xuất hóa đơn",
            "xong",
            "Hóa đơn công ty đã được phát hành",
            f"Hóa đơn điện tử được gửi tới {yeu_cau.email_nhan_hoa_don} từ hệ thống hóa đơn "
            "của nhà thuốc.",
            ma_gia_tri=don.ma_don_hang,
            thoi_diem=yeu_cau.thoi_diem_xu_ly,
        )
        tieu_de = f"Đã xuất hóa đơn công ty cho đơn {don.ma_don_hang}"
    else:
        the = _the(
            "Chưa xuất được",
            "huy",
            "Chưa xuất được hóa đơn công ty",
            "Nhà thuốc chưa thể phát hành hóa đơn theo thông tin đã gửi.",
            ma_gia_tri=don.ma_don_hang,
            thoi_diem=yeu_cau.thoi_diem_xu_ly,
        )
        tieu_de = f"Chưa xuất được hóa đơn công ty – đơn {don.ma_don_hang}"
    email_khach = don.khach_hang.email
    if email_khach:
        nc = _ngu_canh_hoa_don(yeu_cau, the)
        nc.update(
            ghi_chu=yeu_cau.ghi_chu_xu_ly,
            nhan_ghi_chu="Thông tin hóa đơn" if da_xuat else "Lý do",
            cac_luu_y=(
                [_cau_lien_he(don)]
                if da_xuat
                else ["Thông tin cần sửa? Trả lời thư này hoặc gọi nhà thuốc.", _cau_lien_he(don)]
            ),
            nut_chinh=_nut("Xem đơn", nc["url_don"]),
        )
        _gui_thu_don(
            don, loai_email="xuat_hoa_don", tieu_de=tieu_de, mau="xuat_hoa_don", ngu_canh=nc
        )
    # Bản cho kế toán: khi đã xuất, hoặc khi khách không có email để nhận kết quả.
    if yeu_cau.email_nhan_hoa_don == email_khach or (email_khach and not da_xuat):
        return
    from ung_dung.noi_dung.selectors import thong_tin_cua_hang

    nc = _ngu_canh_hoa_don(yeu_cau, {**the, "mo_ta": ""})
    nc.update(
        loi_chao=f"Kính gửi {yeu_cau.ten_cong_ty},",
        the={
            **the,
            "mo_ta": "Nhà thuốc đã xử lý yêu cầu xuất hóa đơn đứng tên công ty cho "
            f"đơn {don.ma_don_hang} tại {thong_tin_cua_hang().ten_thuong_hieu}."
            + (
                " Hóa đơn điện tử được gửi riêng từ hệ thống hóa đơn của nhà thuốc."
                if da_xuat
                else ""
            ),
        },
        ghi_chu=yeu_cau.ghi_chu_xu_ly,
        nhan_ghi_chu="Thông tin hóa đơn" if da_xuat else "Lý do",
        cac_luu_y=[_cau_lien_he(don)],
    )
    gui_email(
        loai_email="xuat_hoa_don",
        email_nhan=yeu_cau.email_nhan_hoa_don,
        tai_khoan=don.khach_hang,
        don_hang=don,
        tieu_de=tieu_de,
        tom_tat=f"{the['tieu_de']}. Đơn {don.ma_don_hang}, {yeu_cau.ten_cong_ty}.",
        ly_do_nhan=f"Bạn nhận thư này vì email được ghi là nơi nhận hóa đơn của {yeu_cau.ten_cong_ty}.",
        mau="xuat_hoa_don",
        ngu_canh=nc,
    )


def bao_xuat_hoa_don(yeu_cau):
    """Gọi sau khi tạo hoặc xử lý yêu cầu hóa đơn công ty; chọn thư theo trạng thái."""
    if yeu_cau.trang_thai == "cho_xu_ly":
        bao_da_nhan_yeu_cau_hoa_don(yeu_cau)
    else:
        bao_ket_qua_hoa_don(yeu_cau)
