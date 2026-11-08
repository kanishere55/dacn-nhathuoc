"""Email gửi khách khi đặt đơn và khi đơn đổi trạng thái."""

from django.conf import settings

from ung_dung.thong_bao.services import gui_email

from .trang_thai import NHAN

LOI_NHAN = {
    "cho_xac_nhan": "Nhà thuốc đã nhận đơn và sẽ xác nhận trong thời gian sớm nhất.",
    "dang_chuan_bi": "Dược sĩ đang soạn thuốc cho đơn của bạn.",
    "dang_giao": "Đơn đã được giao cho người vận chuyển, vui lòng để ý điện thoại.",
    "hoan_thanh": "Đơn đã hoàn tất. Cảm ơn bạn đã tin dùng.",
    "da_huy": "Đơn đã được hủy.",
    "het_han": "Đơn đặt giữ đã quá hạn nhận tại quầy nên hàng được nhả lại.",
    "giao_that_bai": "Người giao không giao được đơn. Nhà thuốc sẽ liên hệ với bạn.",
}


def _ngu_canh(don):
    return {
        "don": don,
        "cac_dong": list(don.cac_dong.select_related("thuoc__don_vi_tinh")),
        "url_don": f"{settings.URL_WEBSITE}/don-hang/{don.pk}/",
        "ho_ten": don.khach_hang.ho_ten or don.khach_hang.ten_dang_nhap,
    }


def bao_don_moi(don):
    if not don.khach_hang.email:
        return
    gui_email(
        loai_email="don_hang_moi",
        email_nhan=don.khach_hang.email,
        tai_khoan=don.khach_hang,
        tieu_de=f"Đã nhận đơn {don.ma_don_hang}",
        mau="don_hang_moi",
        ngu_canh=_ngu_canh(don),
    )


def bao_doi_trang_thai(don, ghi_chu=""):
    if not don.khach_hang.email:
        return
    gui_email(
        loai_email="don_hang_cap_nhat",
        email_nhan=don.khach_hang.email,
        tai_khoan=don.khach_hang,
        tieu_de=f"Đơn {don.ma_don_hang}: {NHAN[don.trang_thai].lower()}",
        mau="don_hang_cap_nhat",
        ngu_canh={
            **_ngu_canh(don),
            "nhan_trang_thai": NHAN[don.trang_thai],
            "loi_nhan": LOI_NHAN.get(don.trang_thai, ""),
            "ghi_chu": ghi_chu,
        },
    )
