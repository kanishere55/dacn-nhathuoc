"""Đối soát tiền của một đơn từ tổng các giao dịch thu và hoàn đã thành công.

Trạng thái thanh toán của đơn không ghi tay theo từng nhánh mà luôn suy ra ở đây:
- phải thu: tổng đơn trừ tiền đã hoàn cho hàng khách trả; bằng 0 khi đơn hủy, hết hạn
  hoặc giao thất bại (khi đó mọi khoản đã thu đều phải hoàn);
- đã thu: tổng thu trừ tổng hoàn;
- còn thiếu = phải thu − đã thu (nếu dương); phải hoàn = đã thu − phải thu (nếu dương).
Không import service của bán hàng để tránh phụ thuộc vòng.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum

from ..models import GiaoDichThanhToan

TRANG_THAI_KHONG_THU = ("da_huy", "het_han", "giao_that_bai")


@dataclass(frozen=True)
class DoiSoat:
    phai_thu: Decimal
    da_thu: Decimal
    da_hoan: Decimal

    @property
    def con_thieu(self):
        return max(self.phai_thu - self.da_thu, Decimal(0))

    @property
    def phai_hoan(self):
        return max(self.da_thu - self.phai_thu, Decimal(0))


def _tong(don, loai):
    return GiaoDichThanhToan.objects.filter(
        don_hang=don, loai_giao_dich=loai, trang_thai="thanh_cong"
    ).aggregate(tong=Sum("so_tien", default=Decimal(0)))["tong"]


def so_tien_da_thu(don):
    """Tiền đơn đang giữ của khách: tổng thu thành công trừ tổng hoàn."""
    return _tong(don, "thu") - _tong(don, "hoan")


def tien_hoan_tra_hang(don):
    from ung_dung.ban_hang.models import YeuCauTraHang

    return YeuCauTraHang.objects.filter(don_hang=don, trang_thai="da_hoan_tien").aggregate(
        tong=Sum("so_tien_hoan", default=Decimal(0))
    )["tong"]


def so_tien_phai_thu(don):
    if don.trang_thai in TRANG_THAI_KHONG_THU:
        return Decimal(0)
    return max(Decimal(don.tong_thanh_toan) - tien_hoan_tra_hang(don), Decimal(0))


def doi_soat(don):
    return DoiSoat(
        phai_thu=so_tien_phai_thu(don), da_thu=so_tien_da_thu(don), da_hoan=_tong(don, "hoan")
    )


def trang_thai_theo_doi_soat(ket_qua):
    if ket_qua.phai_hoan > 0:
        return "cho_hoan_tien"
    if ket_qua.phai_thu > 0:
        return "da_thanh_toan" if ket_qua.da_thu >= ket_qua.phai_thu else "chua_thanh_toan"
    return "da_hoan_tien" if ket_qua.da_hoan > 0 else "chua_thanh_toan"


def cap_nhat_trang_thai_thanh_toan(don):
    """Tính lại trang_thai_thanh_toan của đơn (đơn đã khóa) và lưu nếu đổi; trả DoiSoat."""
    ket_qua = doi_soat(don)
    moi = trang_thai_theo_doi_soat(ket_qua)
    if don.trang_thai == "cho_thanh_toan":
        # Đơn chờ thanh toán chỉ rời trạng thái này qua xác nhận đủ tiền (CHECK của don_hang).
        moi = "chua_thanh_toan"
    if moi != don.trang_thai_thanh_toan:
        don.trang_thai_thanh_toan = moi
        don.save(update_fields=["trang_thai_thanh_toan"])
    return ket_qua
