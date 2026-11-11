"""Nhận tiền từ SePay, MoMo hoặc nhân viên, đối soát và hoàn tiền.

Mỗi khoản tiền là một dòng giao_dich_thanh_toan đúng số tiền nhận được. Một giao dịch ngân
hàng chỉ ghi một lần dù tới từ webhook hay xác nhận tay: mã tham chiếu chuyển khoản là
referenceCode của ngân hàng (SePay gửi kèm, nhân viên chép từ sao kê), duy nhất theo phương
thức. Trạng thái thanh toán của đơn luôn tính lại bằng doi_soat sau mỗi lần ghi.
"""

import json
import logging
import re
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ung_dung.ban_hang.models import DonHang
from ung_dung.ban_hang.services.don_hang import _khoa_don, chuyen_da_thanh_toan
from ung_dung.ban_hang.services.thong_bao_don import (
    bao_da_nhan_tien,
    bao_doi_trang_thai,
    bao_hoan_tien,
)
from ung_dung.ban_hang.services.trang_thai import doi_trang_thai
from ung_dung.chung.permissions import co_quyen, kiem_tra_quyen_ghi_chi_nhanh, thay_toan_chuoi

from .. import momo
from ..models import MA_THAM_CHIEU, PHUONG_THUC, GiaoDichCongDen, GiaoDichThanhToan
from .doi_soat import TRANG_THAI_KHONG_THU, cap_nhat_trang_thai_thanh_toan, doi_soat
from .ghi import ghi_ngay, ket_thuc_cho, tao_cho

nhat_ky = logging.getLogger(__name__)

# Mã đơn hiện tại (DH + yymmdd + 5 ký tự) và mã dài của các đơn tạo trước đó.
CAC_MAU_MA_DON = (
    re.compile(r"DH\d{6}[2-9A-HJKMNP-Z]{5}", re.IGNORECASE),
    re.compile(r"DH[0-9A-F]{20}", re.IGNORECASE),
)
# Lời báo cho người thao tác theo kết quả nhận tiền.
LOI_BAO_NHAN_TIEN = {
    "xac_nhan": "Đã nhận đủ tiền, đơn chuyển sang chờ xác nhận.",
    "thieu": "Đã ghi khoản tiền nhưng khách chuyển chưa đủ; đơn vẫn chờ thanh toán phần còn thiếu.",
    "thua": "Đã ghi khoản tiền; khách đã trả nhiều hơn tổng đơn, phần thừa chuyển sang chờ hoàn.",
    "huy_cho_hoan": "Tiền tới khi đơn đã hủy hoặc quá hạn; khoản này chuyển sang chờ hoàn cho khách.",
    "da_ghi": "Đã ghi khoản tiền vào đơn.",
    "trung": "Khoản tiền này đã được ghi trước đó.",
}
# MoMo: giao dịch đã khởi tạo hoặc đang xử lý thì chưa có kết quả cuối.
MOMO_DANG_XU_LY = {7000, 7002}
MOMO_CHO_KHACH = {1000}


def _so_tien(so):
    return f"{int(so):,} đ".replace(",", ".")


def tim_don_trong_noi_dung(noi_dung):
    cac_ma = {ma.upper() for mau in CAC_MAU_MA_DON for ma in mau.findall(noi_dung)}
    return DonHang.objects.filter(ma_don_hang=cac_ma.pop()).first() if len(cac_ma) == 1 else None


def chuan_hoa_ma_ngan_hang(ma):
    """Mã giao dịch trên sao kê: bỏ khoảng trắng, viết hoa; trả '' nếu sai định dạng."""
    ma = re.sub(r"\s+", "", str(ma or "")).upper()
    return ma if re.fullmatch(MA_THAM_CHIEU, ma) else ""


def _ghi_khoan_thu(don, *, phuong_thuc, so_tien, ma_tham_chieu, nguoi, ghi_chu, giao_dich):
    """Ghi tiền vào đúng dòng: dòng theo orderId (MoMo), dòng chờ của đơn, hoặc dòng mới."""
    bay_gio = timezone.now()
    if giao_dich is not None:
        dong = GiaoDichThanhToan.objects.select_for_update().get(pk=giao_dich.pk)
    else:
        dong = (
            GiaoDichThanhToan.objects.select_for_update()
            .filter(don_hang=don, trang_thai="cho", phuong_thuc=phuong_thuc, loai_giao_dich="thu")
            .order_by("pk")
            .first()
        )
    if dong is not None and dong.trang_thai != "thanh_cong":
        # Tiền về cho dòng đang chờ, kể cả dòng đã bị thay thế hoặc hết hạn: chốt đúng dòng đó.
        dong.trang_thai = "thanh_cong"
        dong.so_tien = so_tien
        dong.ma_tham_chieu = ma_tham_chieu or None
        dong.ghi_chu = ghi_chu
        dong.nguoi_xac_nhan = nguoi
        dong.thoi_diem_hoan_tat = bay_gio
        dong.save()
        return dong
    return ghi_ngay(
        loai="thu",
        phuong_thuc=phuong_thuc,
        so_tien=so_tien,
        don_hang=don,
        nguoi=nguoi,
        ma_tham_chieu=ma_tham_chieu,
        ghi_chu=ghi_chu,
    )


def _gan_cong_den(cong_den, giao_dich):
    if cong_den is None:
        return
    try:
        with transaction.atomic():
            GiaoDichCongDen.objects.filter(pk=cong_den.pk, trang_thai="cho_khop").update(
                trang_thai="da_khop", giao_dich_thanh_toan=giao_dich, ghi_chu_xu_ly=""
            )
    except IntegrityError:
        if not GiaoDichCongDen.objects.filter(giao_dich_thanh_toan=giao_dich).exists():
            raise
        _bo_qua(cong_den, "Trùng khoản tiền đã khớp từ thông báo khác")


def nhan_tien(
    don,
    *,
    phuong_thuc,
    so_tien,
    ma_tham_chieu=None,
    nguoi=None,
    ghi_chu="",
    giao_dich=None,
    cong_den=None,
):
    """Ghi tiền khách đã trả cho đơn rồi đối soát. Trả mã kết quả (xem LOI_BAO_NHAN_TIEN).

    Tiền cộng dồn qua nhiều lần chuyển: đủ tổng trong hạn thì đơn chờ thanh toán sang chờ xác
    nhận; thiếu thì giữ chờ thanh toán; thừa thì phần thừa thành khoản chờ hoàn. Tiền tới khi
    đơn đã hủy hoặc quá hạn (kho có thể đã bán cho người khác) được ghi rồi chờ hoàn toàn bộ.
    """
    try:
        so_tien = Decimal(str(so_tien))
    except InvalidOperation as loi:
        raise ValidationError("Số tiền không hợp lệ.") from loi
    if (
        not so_tien.is_finite()
        or not 0 < so_tien < 10**14
        or so_tien != so_tien.to_integral_value()
    ):
        raise ValidationError("Số tiền nhận phải là số đồng nguyên dương.")
    with transaction.atomic():
        if cong_den is not None:
            cong_den = GiaoDichCongDen.objects.select_for_update().get(pk=cong_den.pk)
            if cong_den.trang_thai != "cho_khop":
                return "trung"
        don = _khoa_don(don, None)
        if ma_tham_chieu:
            da_co = GiaoDichThanhToan.objects.filter(
                phuong_thuc=phuong_thuc, ma_tham_chieu=ma_tham_chieu
            ).first()
            if da_co is not None:
                if da_co.don_hang_id != don.pk or da_co.so_tien != so_tien:
                    raise ValidationError("Mã giao dịch đã được ghi cho đơn hoặc số tiền khác.")
                _gan_cong_den(cong_den, da_co)
                return "trung"
        if don.trang_thai == "cho_thanh_toan" and don.thoi_diem_het_giu <= timezone.now():
            doi_trang_thai(don, "da_huy", None, "Quá hạn thanh toán trực tuyến")
            ket_thuc_cho(don, "het_han")
            vua_qua_han = True
        else:
            vua_qua_han = False
        try:
            with transaction.atomic():
                dong = _ghi_khoan_thu(
                    don,
                    phuong_thuc=phuong_thuc,
                    so_tien=so_tien,
                    ma_tham_chieu=ma_tham_chieu,
                    nguoi=nguoi,
                    ghi_chu=" ".join(str(ghi_chu or "").split())[:200],
                    giao_dich=giao_dich,
                )
        except IntegrityError as loi:
            if (
                ma_tham_chieu
                and GiaoDichThanhToan.objects.filter(
                    phuong_thuc=phuong_thuc, ma_tham_chieu=ma_tham_chieu
                ).exists()
            ):
                raise ValidationError("Mã giao dịch vừa được ghi cho khoản khác.") from loi
            raise
        _gan_cong_den(cong_den, dong)
        ket_qua = doi_soat(don)
        if don.trang_thai == "cho_thanh_toan":
            if ket_qua.da_thu >= don.tong_thanh_toan:
                ten = dict(PHUONG_THUC).get(phuong_thuc, phuong_thuc).lower()
                chuyen_da_thanh_toan(don, nguoi, f"Đã nhận đủ {_so_tien(ket_qua.da_thu)} qua {ten}")
                # Các giao dịch còn chờ khác (ví dụ mã MoMo cũ) không cần nữa.
                ket_thuc_cho(don, "het_han")
                ma_ket_qua = "xac_nhan"
            else:
                ma_ket_qua = "thieu"
        elif don.trang_thai in TRANG_THAI_KHONG_THU:
            ma_ket_qua = "huy_cho_hoan"
        else:
            ma_ket_qua = "da_ghi"
        ket_qua = cap_nhat_trang_thai_thanh_toan(don)
        if vua_qua_han:
            bao_doi_trang_thai(don, "Tiền đến sau khi hết hạn giữ hàng.")
        if ma_ket_qua != "xac_nhan":
            bao_da_nhan_tien(don, dong)
        if ket_qua.phai_hoan > 0 and ma_ket_qua in ("xac_nhan", "da_ghi"):
            ma_ket_qua = "thua"
    return ma_ket_qua


def _luu_cong_den(nguon, ma_doi_tac, *, so_tien, du_lieu, du_lieu_goc, **them):
    """Lưu thông báo đã xác thực; trả (dòng, mới). Thông báo gửi lại chỉ lưu một lần."""
    ma_doi_tac = re.sub(r"[^A-Za-z0-9._:/-]", "", str(ma_doi_tac or ""))[:64]
    if not ma_doi_tac:
        ma_doi_tac = f"khong-ma-{uuid.uuid4().hex}"
    goc = (du_lieu_goc or json.dumps(du_lieu, ensure_ascii=False, sort_keys=True)).strip()
    try:
        so_tien = Decimal(str(so_tien or 0))
        if (
            not so_tien.is_finite()
            or not 0 < so_tien < 10**14
            or so_tien != so_tien.to_integral_value()
        ):
            so_tien = Decimal(0)
    except InvalidOperation:
        so_tien = Decimal(0)
    try:
        with transaction.atomic():
            return GiaoDichCongDen.objects.get_or_create(
                nguon=nguon,
                ma_doi_tac=ma_doi_tac,
                defaults={
                    "so_tien": so_tien,
                    "du_lieu_goc": goc or "{}",
                    "trang_thai": "cho_khop",
                    **them,
                },
            )
    except IntegrityError:
        return GiaoDichCongDen.objects.get(nguon=nguon, ma_doi_tac=ma_doi_tac), False


def _bo_qua(cong_den, ly_do, nguoi=None):
    GiaoDichCongDen.objects.filter(pk=cong_den.pk, trang_thai="cho_khop").update(
        trang_thai="bo_qua", ghi_chu_xu_ly=ly_do[:200], nguoi_xu_ly=nguoi
    )


def xu_ly_sepay(du_lieu, du_lieu_goc=None):
    """Webhook SePay đã qua kiểm khóa: lưu dữ liệu gốc rồi ghi tiền vào đơn có mã trong nội dung."""
    noi_dung = " ".join(str(du_lieu.get("content") or "").split())
    ma_ngan_hang = chuan_hoa_ma_ngan_hang(du_lieu.get("referenceCode"))
    cong_den, moi = _luu_cong_den(
        "sepay",
        du_lieu.get("id"),
        so_tien=du_lieu.get("transferAmount"),
        du_lieu=du_lieu,
        du_lieu_goc=du_lieu_goc,
        ma_tham_chieu=ma_ngan_hang,
        so_tai_khoan_nhan=re.sub(r"[^0-9A-Za-z]", "", str(du_lieu.get("accountNumber") or ""))[:30],
        noi_dung_giao_dich=noi_dung[:500],
    )
    if not moi and cong_den.trang_thai != "cho_khop":
        return "trung"
    if du_lieu.get("transferType") != "in":
        _bo_qua(cong_den, "Không phải tiền vào tài khoản")
        return "bo_qua"
    tai_khoan = cong_den.so_tai_khoan_nhan
    if settings.SO_TAI_KHOAN and tai_khoan and tai_khoan != settings.SO_TAI_KHOAN:
        _bo_qua(
            cong_den, f"Tiền vào tài khoản {tai_khoan}, không phải tài khoản nhận của nhà thuốc"
        )
        return "bo_qua"
    if cong_den.so_tien <= 0:
        _bo_qua(cong_den, "Số tiền bằng 0")
        return "bo_qua"
    don = tim_don_trong_noi_dung(f"{du_lieu.get('code') or ''} {noi_dung}")
    if don is None:
        return "khong_khop"  # để ở trang Tiền chưa khớp cho quản lý gán vào đơn
    return nhan_tien(
        don,
        phuong_thuc="chuyen_khoan",
        so_tien=cong_den.so_tien,
        ma_tham_chieu=ma_ngan_hang or f"sepay-{cong_den.ma_doi_tac}"[:64],
        ghi_chu=noi_dung,
        cong_den=cong_den,
    )


def _ghi_ket_qua_momo(giao_dich, du_lieu, du_lieu_goc=None):
    """Kết quả MoMo đã xác thực cho đúng giao dịch mang orderId đó."""
    ma_ket_qua = str(du_lieu.get("resultCode"))
    trans_id = str(du_lieu.get("transId") or "")
    cong_den, moi = _luu_cong_den(
        "momo",
        f"{du_lieu.get('orderId')}-{trans_id or 'kq' + ma_ket_qua}",
        so_tien=du_lieu.get("amount"),
        du_lieu=du_lieu,
        du_lieu_goc=du_lieu_goc,
        ma_tham_chieu=chuan_hoa_ma_ngan_hang(trans_id),
        noi_dung_giao_dich=" ".join(str(du_lieu.get("message") or "").split())[:500],
    )
    if ma_ket_qua != "0":
        GiaoDichThanhToan.objects.filter(pk=giao_dich.pk, trang_thai="cho").update(
            trang_thai="that_bai",
            ghi_chu=" ".join(str(du_lieu.get("message", "")).split())[:200],
            thoi_diem_hoan_tat=timezone.now(),
        )
        if moi:
            _bo_qua(cong_den, f"MoMo báo chưa thành công (mã {ma_ket_qua})")
        return "that_bai"
    if not moi and cong_den.trang_thai != "cho_khop":
        return "trung"
    return nhan_tien(
        giao_dich.don_hang,
        phuong_thuc="momo",
        so_tien=cong_den.so_tien,
        ma_tham_chieu=f"momo-{trans_id}" if trans_id else None,
        ghi_chu="Thanh toán qua ví MoMo",
        giao_dich=giao_dich,
        cong_den=cong_den,
    )


def xu_ly_ket_qua_momo(du_lieu, du_lieu_goc=None):
    """Kết quả MoMo (IPN hoặc trang quay về) đã kiểm chữ ký."""
    giao_dich = (
        GiaoDichThanhToan.objects.select_related("don_hang")
        .filter(ma_giao_dich_thanh_toan=du_lieu.get("orderId"), phuong_thuc="momo")
        .first()
    )
    if giao_dich is None or giao_dich.don_hang is None:
        cong_den, _ = _luu_cong_den(
            "momo",
            f"{du_lieu.get('orderId')}-{du_lieu.get('transId') or du_lieu.get('resultCode')}",
            so_tien=du_lieu.get("amount"),
            du_lieu=du_lieu,
            du_lieu_goc=du_lieu_goc,
            ma_tham_chieu=chuan_hoa_ma_ngan_hang(du_lieu.get("transId")),
        )
        if str(du_lieu.get("resultCode")) != "0" or not cong_den.so_tien:
            _bo_qua(cong_den, "MoMo chưa xác nhận đã thu tiền")
            return "that_bai"
        return "khong_khop"
    return _ghi_ket_qua_momo(giao_dich, du_lieu, du_lieu_goc)


def _hoi_momo(giao_dich):
    """Hỏi MoMo trạng thái một giao dịch đang chờ: 'da_tra', 'dang_xu_ly' hoặc None."""
    try:
        ket_qua = momo.truy_van(giao_dich.ma_giao_dich_thanh_toan)
    except ValidationError:
        return None
    ma = ket_qua.get("resultCode")
    if ma == 0:
        _ghi_ket_qua_momo(giao_dich, {**ket_qua, "orderId": giao_dich.ma_giao_dich_thanh_toan})
        return "da_tra"
    if ma in MOMO_DANG_XU_LY:
        return "dang_xu_ly"
    if ma not in MOMO_CHO_KHACH:
        GiaoDichThanhToan.objects.filter(pk=giao_dich.pk, trang_thai="cho").update(
            trang_thai="that_bai",
            ghi_chu=" ".join(str(ket_qua.get("message", "")).split())[:200],
            thoi_diem_hoan_tat=timezone.now(),
        )
    return None


def _kiem_don_momo(nguoi, don):
    if nguoi.vai_tro != "khach_hang" or don.khach_hang_id != nguoi.pk:
        raise PermissionDenied("Đơn không thuộc tài khoản của bạn.")
    if don.phuong_thuc_thanh_toan != "momo" or don.trang_thai != "cho_thanh_toan":
        raise ValidationError("Đơn không còn chờ thanh toán qua MoMo.")
    if don.thoi_diem_het_giu <= timezone.now():
        raise ValidationError("Đơn đã quá hạn thanh toán, hàng đã được nhả. Hãy đặt đơn mới.")


def kiem_tra_momo(nguoi, don):
    """Khách bấm "Tôi đã trả, kiểm tra lại": hỏi MoMo các giao dịch đang chờ của đơn."""
    _kiem_don_momo(nguoi, don)
    ket_qua = None
    for giao_dich in GiaoDichThanhToan.objects.filter(
        don_hang=don, phuong_thuc="momo", trang_thai="cho"
    ).order_by("pk"):
        ket_qua = _hoi_momo(giao_dich) or ket_qua
        if ket_qua == "da_tra":
            break
    return ket_qua or "chua_tra"


def bat_dau_momo(nguoi, don, url_quay_ve, url_ipn):
    """Tạo yêu cầu thanh toán MoMo mới; trả (kết quả, payUrl).

    Trước khi tạo mới, hỏi MoMo các giao dịch đang chờ (gọi mạng ngoài transaction để không
    giữ khóa kho): đã trả thì ghi nhận và không tạo mới, đang xử lý thì báo khách chờ.
    """
    _kiem_don_momo(nguoi, don)
    ket_qua = kiem_tra_momo(nguoi, don)
    if ket_qua in ("da_tra", "dang_xu_ly"):
        return ket_qua, None
    with transaction.atomic():
        don = _khoa_don(don, nguoi)
        _kiem_don_momo(nguoi, don)
        # MoMo không nhận lại mã đơn đã gửi: mỗi lần là một giao dịch chờ mới; dòng cũ
        # chuyển hết hạn nhưng nếu tiền vẫn về theo mã cũ thì vẫn được ghi đúng dòng đó.
        GiaoDichThanhToan.objects.filter(don_hang=don, phuong_thuc="momo", trang_thai="cho").update(
            trang_thai="het_han", thoi_diem_hoan_tat=timezone.now()
        )
        giao_dich = tao_cho(don, "momo")
    try:
        url = momo.tao_thanh_toan(
            giao_dich.ma_giao_dich_thanh_toan,
            don.tong_thanh_toan,
            f"Thanh toan don {don.ma_don_hang}",
            url_quay_ve,
            url_ipn,
        )
    except ValidationError as loi:
        GiaoDichThanhToan.objects.filter(pk=giao_dich.pk, trang_thai="cho").update(
            trang_thai="that_bai",
            ghi_chu=" ".join(loi.messages)[:200],
            thoi_diem_hoan_tat=timezone.now(),
        )
        raise
    return "chuyen", url


@transaction.atomic
def xac_nhan_tay(nguoi, don, ma_giao_dich="", so_tien=None):
    """Quản lý đối chiếu sao kê và ghi khoản chuyển khoản khách đã chuyển.

    Bắt buộc mã giao dịch ngân hàng (referenceCode trên sao kê), là mã SePay cũng gửi: ghi
    tay trước rồi webhook tới sau (hoặc ngược lại) thì chỉ còn một dòng. Không nhập số tiền
    thì ghi đúng phần còn thiếu của đơn.
    """
    don = _khoa_don(don, nguoi, "thanh_toan.xac_nhan")
    if don.phuong_thuc_thanh_toan != "chuyen_khoan":
        raise ValidationError(
            "Chỉ xác nhận tay cho đơn chuyển khoản VietQR; đơn MoMo được MoMo báo kết quả."
        )
    if don.trang_thai != "cho_thanh_toan":
        raise ValidationError("Đơn không ở trạng thái chờ thanh toán.")
    ma = chuan_hoa_ma_ngan_hang(ma_giao_dich)
    if not ma:
        raise ValidationError(
            "Nhập mã giao dịch trên sao kê ngân hàng (ví dụ FT26315123456) để không ghi trùng."
        )
    so_tien = so_tien or doi_soat(don).con_thieu or don.tong_thanh_toan
    ket_qua = nhan_tien(
        don,
        phuong_thuc="chuyen_khoan",
        so_tien=so_tien,
        ma_tham_chieu=ma,
        nguoi=nguoi,
        ghi_chu="Nhân viên đối chiếu sao kê ngân hàng",
    )
    if ket_qua == "trung":
        raise ValidationError(
            f"Mã giao dịch {ma} đã được ghi trước đó (có thể ngân hàng đã tự báo). "
            "Không ghi lại lần nữa."
        )
    return ket_qua


@transaction.atomic
def da_thu_tien_cod(nguoi, don, ghi_chu=""):
    """Nhân sự nhận tiền người giao nộp lại: chốt khoản COD đang chờ đối soát của đơn."""
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, don.chi_nhanh, "thanh_toan.xac_nhan")
    don = _khoa_don(don, nguoi, "thanh_toan.xac_nhan")
    dong = (
        GiaoDichThanhToan.objects.select_for_update()
        .filter(don_hang=don, phuong_thuc="cod", trang_thai="cho")
        .first()
    )
    if dong is None:
        raise ValidationError("Đơn không có khoản COD nào đang chờ đối soát.")
    dong.trang_thai = "thanh_cong"
    dong.nguoi_xac_nhan = nguoi
    dong.thoi_diem_hoan_tat = timezone.now()
    dong.ghi_chu = " ".join((ghi_chu or "Đã nhận tiền COD từ người giao").split())[:200]
    dong.save()
    cap_nhat_trang_thai_thanh_toan(don)
    return dong


@transaction.atomic
def hoan_tien(nguoi, don, *, phuong_thuc, ma_tham_chieu="", ghi_chu=""):
    """Quản lý ghi nhận đã trả lại đúng phần phải hoàn của đơn (thừa hoặc đơn đã hủy)."""
    if nguoi is None:
        raise PermissionDenied("Hoàn tiền cần người xác nhận.")
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, don.chi_nhanh, "don_hang.hoan_tien")
    don = _khoa_don(don, nguoi, "don_hang.hoan_tien")
    so_tien = doi_soat(don).phai_hoan
    if so_tien <= 0:
        raise ValidationError("Đơn không có khoản phải hoàn cho khách.")
    giao_dich = ghi_ngay(
        loai="hoan",
        phuong_thuc=phuong_thuc,
        so_tien=so_tien,
        don_hang=don,
        nguoi=nguoi,
        ma_tham_chieu=f"hoan-{ma_tham_chieu}" if ma_tham_chieu else None,
        ghi_chu=ghi_chu or "Hoàn tiền cho khách",
    )
    cap_nhat_trang_thai_thanh_toan(don)
    bao_hoan_tien(don, giao_dich)
    return don


@transaction.atomic
def gan_tien_vao_don(nguoi, cong_den, ma_don_hang, ghi_chu=""):
    """Quản lý gán khoản tiền chưa khớp (khách ghi sai nội dung) vào đúng đơn."""
    if not thay_toan_chuoi(nguoi) or not co_quyen(nguoi, "thanh_toan.xac_nhan"):
        raise PermissionDenied("Đối soát tiền chưa khớp cần quyền toàn chuỗi.")
    cong_den = GiaoDichCongDen.objects.select_for_update().get(pk=cong_den.pk)
    if cong_den.trang_thai != "cho_khop":
        raise ValidationError("Khoản tiền này đã được xử lý.")
    don = DonHang.objects.filter(ma_don_hang=" ".join(ma_don_hang.split()).upper()).first()
    if don is None:
        raise ValidationError("Không tìm thấy đơn có mã này.")
    kiem_tra_quyen_ghi_chi_nhanh(nguoi, don.chi_nhanh, "thanh_toan.xac_nhan")
    phuong_thuc = "momo" if cong_den.nguon == "momo" else "chuyen_khoan"
    ma = cong_den.ma_tham_chieu or f"{cong_den.nguon}-{cong_den.ma_doi_tac}"[:64]
    if phuong_thuc == "momo":
        ma = f"momo-{cong_den.ma_tham_chieu}" if cong_den.ma_tham_chieu else None
    ket_qua = nhan_tien(
        don,
        phuong_thuc=phuong_thuc,
        so_tien=cong_den.so_tien,
        ma_tham_chieu=ma,
        nguoi=nguoi,
        ghi_chu=ghi_chu or f"Quản lý gán khoản tiền chưa khớp: {cong_den.noi_dung_giao_dich}",
        cong_den=cong_den,
    )
    GiaoDichCongDen.objects.filter(pk=cong_den.pk).update(nguoi_xu_ly=nguoi)
    return don, ket_qua


@transaction.atomic
def bo_qua_tien_chua_khop(nguoi, cong_den, ly_do):
    """Ghi chú khoản tiền không thuộc đơn nào (đã hoàn ngoài hệ thống, tiền khác...)."""
    if not thay_toan_chuoi(nguoi) or not co_quyen(nguoi, "thanh_toan.xac_nhan"):
        raise PermissionDenied("Đối soát tiền chưa khớp cần quyền toàn chuỗi.")
    ly_do = " ".join(str(ly_do or "").split())
    if not ly_do:
        raise ValidationError("Ghi rõ đã xử lý khoản tiền này thế nào, ví dụ đã hoàn cho khách.")
    cong_den = GiaoDichCongDen.objects.select_for_update().get(pk=cong_den.pk)
    if cong_den.trang_thai != "cho_khop":
        raise ValidationError("Khoản tiền này đã được xử lý.")
    _bo_qua(cong_den, ly_do, nguoi)
    return cong_den
