"""Email gửi khách theo từng sự kiện của đơn đặt giữ: đặt giữ, đổi trạng thái (đã nhận hàng,
hủy, hết hạn) và hóa đơn công ty.

Mỗi thư nói rõ khách cần làm gì tiếp theo, kèm hạn bằng giờ tuyệt đối và nút đi thẳng tới
đúng trang (chỉ đường tới chi nhánh, đơn, hóa đơn). Nội dung dựng ở đây; trình bày nằm trong
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
    "dang_giu": "dang",
    "hoan_thanh": "xong",
    "da_huy": "huy",
    "het_han": "trung_tinh",
}
# Các bước trên dòng tiến trình của đơn đặt giữ.
BUOC = ["dang_giu", "hoan_thanh"]


def _gio(thoi_diem):
    return timezone.localtime(thoi_diem).strftime("%H:%M %d/%m/%Y") if thoi_diem else ""


def _tien(so_tien):
    return tien(so_tien).replace(" ", " ")


def tien_trinh(don):
    """[(nhãn, đã qua, hiện tại)] cho dòng tiến trình; rỗng khi đơn đã kết thúc bất thường."""
    if don.trang_thai not in BUOC:
        return []
    vi_tri = BUOC.index(don.trang_thai)
    return [(NHAN[buoc], so <= vi_tri, so == vi_tri) for so, buoc in enumerate(BUOC)]


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

    if tt == "dang_giu":
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
    elif tt == "hoan_thanh":
        co_phieu = phieu is not None
        the = _the(
            nhan,
            nhom,
            "Đơn đã hoàn tất, cảm ơn bạn",
            "Bạn có thể mở hoặc tải hóa đơn bán lẻ từ nút bên dưới." if co_phieu else "",
            ma_gia_tri=ma,
        )
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
    if tt in ("da_huy", "het_han"):
        luu_y.append(_cau_lien_he(don))
    nc.update(the=the, ghi_chu=ghi_chu)
    return tieu_de, nc


def bao_don_moi(don):
    if not don.khach_hang.email:
        return
    tieu_de, nc = _noi_dung_theo_trang_thai(don)
    _gui_thu_don(don, loai_email="don_hang_moi", tieu_de=tieu_de, mau="don_hang_moi", ngu_canh=nc)


def bao_doi_trang_thai(don, ghi_chu=""):
    """Thư khi đơn đổi trạng thái; `ghi_chu` là lý do hủy hoặc hết hạn gửi nguyên văn cho khách.

    Đơn hoàn thành (khách đã nhận và trả tiền tại quầy) kèm hóa đơn bán lẻ PDF.
    """
    if not don.khach_hang.email:
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
