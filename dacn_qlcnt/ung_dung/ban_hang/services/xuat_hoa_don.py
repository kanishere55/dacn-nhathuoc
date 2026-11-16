"""Yêu cầu hóa đơn đứng tên doanh nghiệp cho một đơn.

Hệ thống chỉ ghi nhận thông tin người mua và kết quả xử lý. Hóa đơn điện tử có mã của cơ
quan thuế được nhân viên phát hành trên phần mềm hóa đơn của nhà thuốc, rồi ghi ký hiệu và
số hóa đơn vào đây để khách tra cứu.

Thời điểm lập hóa đơn bán hàng là lúc chuyển giao hàng hóa (Nghị định 123/2020/NĐ-CP Điều 9,
sửa đổi bởi Nghị định 70/2025/NĐ-CP), tức lúc khách nhận thuốc tại quầy, nên thông tin công ty
nhận từ lúc đặt giữ. Đơn đã nhận hàng còn gửi được tới hết tháng nhận hàng để nhà thuốc kịp lập
hoặc điều chỉnh trong kỳ.
"""

import re
from datetime import date

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_quyen_ghi_chi_nhanh, kiem_tra_vai_tro
from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import (
    KY_HIEU_HOA_DON,
    SO_HOA_DON,
    TRANG_THAI_GIU,
    DonHang,
    LichSuDonHang,
    YeuCauXuatHoaDon,
)
from .thong_bao_don import bao_xuat_hoa_don

TRANG_THAI_KHONG_NHAN = ("da_huy", "het_han")


def thoi_diem_hoan_thanh(don):
    """Lúc khách nhận hàng tại quầy (đơn chuyển hoàn thành); None khi chưa nhận."""
    lich_su = (
        LichSuDonHang.objects.filter(don_hang=don, den_trang_thai="hoan_thanh")
        .order_by("-thoi_diem_tao")
        .first()
    )
    return lich_su.thoi_diem_tao if lich_su else None


def han_yeu_cau_hoa_don(don):
    """Ngày cuối gửi yêu cầu: hết tháng khách nhận hàng; None khi đơn chưa hoàn thành."""
    xong = thoi_diem_hoan_thanh(don) if don.trang_thai == "hoan_thanh" else None
    if xong is None:
        return None
    ngay = timezone.localdate(xong)
    dau_thang_sau = date(ngay.year + (ngay.month == 12), ngay.month % 12 + 1, 1)
    return date.fromordinal(dau_thang_sau.toordinal() - 1)


def ly_do_khong_yeu_cau_duoc(don):
    """Câu giải thích vì sao đơn chưa gửi được yêu cầu hóa đơn công ty; None nếu được gửi."""
    if don.trang_thai in TRANG_THAI_KHONG_NHAN:
        return "Đơn đã hủy hoặc hết hạn giữ nên không xuất hóa đơn."
    if don.trang_thai in TRANG_THAI_GIU and don.thoi_diem_het_giu <= timezone.now():
        return "Đơn đã quá hạn giữ hàng."
    han = han_yeu_cau_hoa_don(don)
    if han is not None and timezone.localdate() > han:
        return (
            f"Đã hết hạn gửi thông tin hóa đơn công ty (hết ngày {han:%d/%m/%Y}). "
            "Vui lòng liên hệ nhà thuốc."
        )
    if YeuCauXuatHoaDon.objects.filter(don_hang=don).exists():
        return "Đơn này đã có yêu cầu xuất hóa đơn."
    return None


@transaction.atomic
def gui_yeu_cau_xuat_hoa_don(nguoi, don, thong_tin):
    kiem_tra_vai_tro(nguoi, "khach_hang")
    don = DonHang.objects.select_for_update().get(pk=don.pk)
    if don.khach_hang_id != nguoi.pk:
        raise PermissionDenied("Đơn không thuộc tài khoản của bạn.")
    ly_do = ly_do_khong_yeu_cau_duoc(don)
    if ly_do:
        raise ValidationError(ly_do)
    yeu_cau = YeuCauXuatHoaDon(
        don_hang=don,
        ten_cong_ty=cat_khoang_trang(thong_tin["ten_cong_ty"]),
        ma_so_thue=cat_khoang_trang(thong_tin["ma_so_thue"]),
        dia_chi_cong_ty=cat_khoang_trang(thong_tin["dia_chi_cong_ty"]),
        email_nhan_hoa_don=cat_khoang_trang(thong_tin["email_nhan_hoa_don"]).lower(),
    )
    yeu_cau.full_clean()
    yeu_cau.save()
    bao_xuat_hoa_don(yeu_cau)
    return yeu_cau


@transaction.atomic
def xu_ly_yeu_cau_xuat_hoa_don(
    nguoi, yeu_cau, trang_thai, *, ky_hieu_hoa_don="", so_hoa_don="", ly_do_tu_choi=""
):
    """Ghi kết quả: đã xuất (ký hiệu + số hóa đơn) hoặc từ chối (lý do)."""
    yeu_cau = (
        YeuCauXuatHoaDon.objects.select_for_update(of=("self", "don_hang"))
        .select_related("don_hang__chi_nhanh", "don_hang__khach_hang")
        .get(pk=yeu_cau.pk)
    )
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, yeu_cau.don_hang.chi_nhanh, "hoa_don_cong_ty.xu_ly")
    if yeu_cau.trang_thai != "cho_xu_ly":
        raise ValidationError("Yêu cầu này đã được xử lý.")
    if trang_thai == "da_xuat":
        ky_hieu = cat_khoang_trang(ky_hieu_hoa_don).replace(" ", "").upper()
        so = cat_khoang_trang(so_hoa_don).replace(" ", "")
        if not ky_hieu or not so:
            raise ValidationError("Ghi đủ ký hiệu và số của hóa đơn điện tử đã phát hành.")
        if not re.fullmatch(KY_HIEU_HOA_DON, ky_hieu):
            raise ValidationError(
                "Ký hiệu hóa đơn gồm 7 ký tự như trên hóa đơn, ví dụ 1C26TAA "
                "(số mẫu, C hoặc K, hai số cuối năm, ba chữ cái)."
            )
        if not re.fullmatch(SO_HOA_DON, so):
            raise ValidationError("Số hóa đơn gồm 1 đến 8 chữ số, ví dụ 0000123.")
        trung = (
            YeuCauXuatHoaDon.objects.filter(
                trang_thai="da_xuat", ky_hieu_hoa_don=ky_hieu, so_hoa_don=so
            )
            .select_related("don_hang")
            .first()
        )
        if trung:
            raise ValidationError(
                f"Hóa đơn {ky_hieu} số {so} đã được ghi cho đơn {trung.don_hang.ma_don_hang}."
            )
        if yeu_cau.don_hang.trang_thai in TRANG_THAI_KHONG_NHAN:
            raise ValidationError("Đơn đã hủy hoặc hết hạn giữ, không ghi hóa đơn cho đơn này.")
        if yeu_cau.don_hang.trang_thai != "hoan_thanh":
            raise ValidationError("Chờ xác nhận khách đã nhận hàng trước khi ghi hóa đơn đã xuất.")
        yeu_cau.ky_hieu_hoa_don, yeu_cau.so_hoa_don = ky_hieu, so
        yeu_cau.ghi_chu_xu_ly = f"Hóa đơn điện tử ký hiệu {ky_hieu}, số {so}"
    elif trang_thai == "tu_choi":
        ly_do = cat_khoang_trang(ly_do_tu_choi)
        if not ly_do:
            raise ValidationError("Ghi lý do từ chối để khách nắm được.")
        yeu_cau.ly_do_tu_choi = ly_do
        yeu_cau.ghi_chu_xu_ly = ly_do
    else:
        raise ValidationError("Kết quả xử lý không hợp lệ.")
    yeu_cau.trang_thai = trang_thai
    yeu_cau.nguoi_xu_ly = nguoi
    yeu_cau.thoi_diem_xu_ly = timezone.now()
    yeu_cau.full_clean()
    try:
        with transaction.atomic():
            yeu_cau.save()
    except IntegrityError as loi:
        if getattr(getattr(loi.__cause__, "diag", None), "constraint_name", None) != (
            "duy_nhat__xuat_hoa_don__ky_hieu_hoa_don__so_hoa_don"
        ):
            raise
        raise ValidationError("Ký hiệu và số hóa đơn này vừa được ghi cho đơn khác.") from loi
    bao_xuat_hoa_don(yeu_cau)
    return yeu_cau
