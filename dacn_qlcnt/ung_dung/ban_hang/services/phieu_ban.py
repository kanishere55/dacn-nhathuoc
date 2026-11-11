import re
from datetime import date
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.permissions import co_quyen
from ung_dung.danh_muc.models import Thuoc
from ung_dung.danh_muc.selectors import them_gia_va_anh
from ung_dung.kho.services.giao_dich import (
    doi_ve_co_so,
    khoa_chi_nhanh,
    ma_chung_tu,
    phan_bo_fefo,
    thay_doi_ton,
)
from ung_dung.thanh_toan.services.doi_soat import cap_nhat_trang_thai_thanh_toan, doi_soat
from ung_dung.thanh_toan.services.ghi import ghi_ngay

from ..models import (
    MA_DON_THUOC,
    TRANG_THAI_GIU,
    ChiTietPhieuBan,
    DonHang,
    PhanBoPhieuBan,
    PhieuBan,
)
from ..selectors import tong_tien_ban
from .giao_hang import han_toi_thieu_giao
from .thong_bao_don import bao_doi_trang_thai
from .trang_thai import doi_trang_thai, kiem_tra_chuyen

THONG_BAO_KE_DON = (
    "Phiếu có thuốc kê đơn: dược sĩ phải kiểm tra đơn thuốc, ghi họ tên bác sĩ kê đơn, "
    "cơ sở khám bệnh, họ tên người bệnh và ngày kê đơn."
)
THONG_BAO_QUYEN_KE_DON = (
    "Phiếu có thuốc kê đơn: chỉ dược sĩ được giao quyền bán thuốc kê đơn mới lập được. "
    "Hãy nhờ dược sĩ hoặc quản lý chi nhánh thực hiện."
)
PHUONG_THUC_TAI_QUAY = ("tien_mat", "chuyen_khoan")


def _thong_tin_don_thuoc(co_ke_don, don_thuoc):
    """Chuẩn hóa thông tin đơn thuốc; phiếu không có thuốc kê đơn thì bỏ trống."""
    if not co_ke_don:
        return {
            "da_kiem_tra_don_thuoc": False,
            "ma_don_thuoc": None,
            "ten_nguoi_ke_don": "",
            "noi_kham_benh": "",
            "ngay_ke_don": None,
            "ho_ten_nguoi_benh": "",
        }
    don_thuoc = don_thuoc or {}
    ngay_ke_don = don_thuoc.get("ngay_ke_don")
    if ngay_ke_don is not None and not isinstance(ngay_ke_don, date):
        raise ValidationError("Ngày kê đơn không hợp lệ.")
    thong_tin = {
        "da_kiem_tra_don_thuoc": bool(don_thuoc.get("da_kiem_tra_don_thuoc")),
        "ma_don_thuoc": " ".join(str(don_thuoc.get("ma_don_thuoc") or "").split()) or None,
        "ten_nguoi_ke_don": " ".join(str(don_thuoc.get("ten_nguoi_ke_don") or "").split()),
        "noi_kham_benh": " ".join(str(don_thuoc.get("noi_kham_benh") or "").split()),
        "ngay_ke_don": ngay_ke_don,
        "ho_ten_nguoi_benh": " ".join(str(don_thuoc.get("ho_ten_nguoi_benh") or "").split()),
    }
    if not (
        thong_tin["da_kiem_tra_don_thuoc"]
        and thong_tin["ten_nguoi_ke_don"]
        and thong_tin["noi_kham_benh"]
        and thong_tin["ngay_ke_don"]
        and thong_tin["ho_ten_nguoi_benh"]
    ):
        raise ValidationError(THONG_BAO_KE_DON)
    if thong_tin["ngay_ke_don"] > timezone.localdate():
        raise ValidationError("Ngày kê đơn không thể sau hôm nay.")
    ma = thong_tin["ma_don_thuoc"]
    if ma and not re.fullmatch(MA_DON_THUOC, ma):
        raise ValidationError("Mã đơn thuốc gồm 6–30 chữ, số hoặc dấu gạch ngang.")
    if (
        len(thong_tin["ten_nguoi_ke_don"]) > 120
        or len(thong_tin["noi_kham_benh"]) > 200
        or len(thong_tin["ho_ten_nguoi_benh"]) > 120
    ):
        raise ValidationError("Tên bác sĩ, cơ sở khám bệnh hoặc tên người bệnh quá dài.")
    return thong_tin


def thong_bao_qua_han(don_hang):
    """Lời báo khi đơn đang giữ hàng đã qua hạn mà lệnh định kỳ chưa kịp đổi trạng thái."""
    han = timezone.localtime(don_hang.thoi_diem_het_giu)
    if don_hang.trang_thai == "dang_giu":
        return (
            f"Đơn đã quá hạn giữ lúc {han:%H:%M %d/%m/%Y}, hàng đã được nhả cho khách khác. "
            "Nếu khách vẫn mua, hãy lập phiếu bán trực tiếp tại quầy."
        )
    return f"Đơn đã quá hạn xác nhận lúc {han:%H:%M %d/%m/%Y}; hệ thống sẽ hủy đơn" + (
        " và chuyển tiền khách đã trả sang chờ hoàn."
        if don_hang.phuong_thuc_thanh_toan != "cod"
        else "."
    )


@transaction.atomic
def ban_tai_quay(
    nguoi,
    chi_nhanh,
    cac_dong,
    *,
    khoa_yeu_cau=None,
    don_hang=None,
    don_thuoc=None,
    phuong_thuc_thanh_toan="tien_mat",
):
    """Lập phiếu bán và xuất kho FEFO.

    Có `don_hang`: xuất đúng các dòng của đơn với giá đã chụp lúc đặt. Đơn nhận tại
    quầy chuyển hoàn thành (khách nhận và trả tiền), đơn giao hàng chuyển đang chuẩn bị.
    Không có đơn: bán trực tiếp theo giá đang áp dụng. `don_thuoc` gồm
    da_kiem_tra_don_thuoc, ma_don_thuoc, ten_nguoi_ke_don, noi_kham_benh và chỉ bắt
    buộc khi phiếu có thuốc kê đơn, cùng ngay_ke_don và ho_ten_nguoi_benh. Phiếu có thuốc kê
    đơn cần quyền thuoc_ke_don.ban (dược sĩ). Đơn giao hàng chỉ xuất lô còn hạn ít nhất 30
    ngày. Đơn đã trả trước một phần hoặc đủ thì quầy chỉ thu phần còn thiếu.
    """
    if phuong_thuc_thanh_toan not in PHUONG_THUC_TAI_QUAY:
        raise ValidationError("Tại quầy chỉ nhận tiền mặt hoặc chuyển khoản.")
    khoa_chi_nhanh(nguoi, chi_nhanh, "don_hang.xu_ly" if don_hang else "phieu_ban.tao")
    khoa_yeu_cau = str(khoa_yeu_cau or uuid4())
    da_co = PhieuBan.objects.filter(
        khoa_yeu_cau=khoa_yeu_cau, nguoi_lap=nguoi, chi_nhanh=chi_nhanh
    ).first()
    if da_co:
        return da_co
    if don_hang:
        don_hang = DonHang.objects.select_for_update().get(pk=don_hang.pk)
        if don_hang.chi_nhanh_id != chi_nhanh.pk:
            raise ValidationError("Đơn không thuộc chi nhánh bán.")
        da_ban = PhieuBan.objects.filter(don_hang=don_hang).first()
        if da_ban:
            return da_ban
        den = "hoan_thanh" if don_hang.hinh_thuc_nhan == "nhan_tai_quay" else "dang_chuan_bi"
        kiem_tra_chuyen(don_hang, den, nguoi)
        # Cùng quy tắc hạn ở mọi đường đi, không phụ thuộc lệnh định kỳ đã chạy hay chưa.
        if don_hang.trang_thai in TRANG_THAI_GIU and don_hang.thoi_diem_het_giu <= timezone.now():
            raise ValidationError(thong_bao_qua_han(don_hang))
        cac_dong = [
            {
                "thuoc": dong.thuoc,
                "so_luong": dong.so_luong,
                "don_gia": dong.don_gia,
                "giam_gia_phan_bo": dong.giam_gia_phan_bo,
            }
            for dong in don_hang.cac_dong.select_related("thuoc")
        ]
    if not cac_dong:
        raise ValidationError("Phiếu bán cần ít nhất một thuốc.")
    cac_thuoc = them_gia_va_anh(
        Thuoc.objects.filter(pk__in=[dong["thuoc"].pk for dong in cac_dong]).select_related(
            "don_vi_tinh"
        )
    ).in_bulk()
    ngung = [t.ten_thuoc for t in cac_thuoc.values() if not t.dang_hoat_dong]
    if ngung:
        raise ValidationError(f"{', '.join(ngung)} đã ngừng kinh doanh, không bán được.")
    co_ke_don = any(t.la_thuoc_ke_don for t in cac_thuoc.values())
    if co_ke_don and not co_quyen(nguoi, "thuoc_ke_don.ban"):
        raise PermissionDenied(THONG_BAO_QUYEN_KE_DON)
    thong_tin_don = _thong_tin_don_thuoc(co_ke_don, don_thuoc)
    con_han_den = (
        han_toi_thieu_giao() if don_hang and don_hang.hinh_thuc_nhan == "giao_hang" else None
    )
    phieu = PhieuBan(
        ma_phieu_ban=ma_chung_tu("BH"),
        khoa_yeu_cau=khoa_yeu_cau,
        chi_nhanh=chi_nhanh,
        nguoi_lap=nguoi,
        don_hang=don_hang,
        **thong_tin_don,
    )
    phieu.save()
    for dong in cac_dong:
        thuoc = cac_thuoc[dong["thuoc"].pk]
        luong = doi_ve_co_so(thuoc, dong["so_luong"], dong.get("quy_doi_bao_goi"))
        chi_tiet = ChiTietPhieuBan(
            phieu_ban=phieu,
            thuoc=thuoc,
            ma_thuoc_luc_ban=thuoc.ma_thuoc,
            ten_thuoc_luc_ban=thuoc.ten_thuoc,
            so_luong=luong,
            don_gia=dong.get("don_gia", thuoc.don_gia),
            giam_gia_phan_bo=dong.get("giam_gia_phan_bo", 0),
        )
        chi_tiet.full_clean()
        chi_tiet.save()
        for ton, lay in phan_bo_fefo(
            chi_nhanh, thuoc, luong, bo_qua_don=don_hang, con_han_den=con_han_den
        ):
            thay_doi_ton(ton, -lay)
            PhanBoPhieuBan.objects.create(chi_tiet_phieu_ban=chi_tiet, ton_kho=ton, so_luong=lay)
    if not don_hang:
        ghi_ngay(
            loai="thu",
            phuong_thuc=phuong_thuc_thanh_toan,
            so_tien=tong_tien_ban(phieu),
            phieu_ban=phieu,
            nguoi=nguoi,
            ghi_chu="Thu tại quầy",
        )
        return phieu
    doi_trang_thai(don_hang, den, nguoi, f"Lập phiếu bán {phieu.ma_phieu_ban}")
    if den == "hoan_thanh":
        # Khách nhận tại quầy: chỉ thu phần còn thiếu (đơn có thể đã chuyển khoản trước).
        con_thieu = doi_soat(don_hang).con_thieu
        if con_thieu > 0:
            ghi_ngay(
                loai="thu",
                phuong_thuc=phuong_thuc_thanh_toan,
                so_tien=con_thieu,
                don_hang=don_hang,
                phieu_ban=phieu,
                nguoi=nguoi,
                ghi_chu="Thu tại quầy",
            )
        cap_nhat_trang_thai_thanh_toan(don_hang)
    bao_doi_trang_thai(don_hang)
    return phieu
