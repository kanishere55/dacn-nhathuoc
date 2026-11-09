"""Mã OTP qua email cho đăng ký, quên mật khẩu, đổi email và nhắc tên đăng nhập.

Mã sáu chữ số chỉ tồn tại trong bộ nhớ khi gửi; CSDL giữ HMAC-SHA256 của
"ma_phien:ma_otp" với khóa SECRET_KEY. Mỗi phiên hết hạn sau 10 phút, khóa sau
5 lần nhập sai, gửi lại tối đa 5 lần và cách nhau ít nhất 60 giây. Mỗi email chỉ
được mở 5 phiên mỗi giờ.
"""

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ung_dung.thong_bao.services import gui_email, ten_thuong_hieu

from ..models import PhienXacThuc, tao_ma_uuid

GIAY_CHO_GUI_LAI = 60
SO_PHIEN_MOI_GIO = 5
SO_NHAC_TEN_MOI_GIO = 3
MUC_DICH = {
    "dang_ky": "hoàn tất đăng ký tài khoản",
    "quen_mat_khau": "đặt lại mật khẩu",
    "doi_email": "xác nhận email mới",
}


def _bam(ma_phien, ma_otp):
    return hmac.new(
        settings.SECRET_KEY.encode(), f"{ma_phien}:{ma_otp}".encode(), hashlib.sha256
    ).hexdigest()


def _tao_otp():
    return f"{secrets.randbelow(10**6):06d}"


def _gui_ma(phien, ma_otp, ho_ten=""):
    gui_email(
        loai_email="ma_xac_thuc",
        email_nhan=phien.email,
        tai_khoan=phien.tai_khoan,
        tieu_de=f"Mã xác thực {ten_thuong_hieu()}",
        mau="ma_xac_thuc",
        ngu_canh={
            "ho_ten": ho_ten,
            "ma_otp": ma_otp,
            "muc_dich": MUC_DICH[phien.loai_xac_thuc],
            "so_phut": PhienXacThuc.SO_PHUT_HIEU_LUC,
        },
    )


def _tao_phien(loai, email, *, tai_khoan=None, gui=True, ho_ten="", **dang_ky):
    bay_gio = timezone.now()
    so_phien = PhienXacThuc.objects.filter(
        email=email, thoi_diem_tao__gte=bay_gio - timedelta(hours=1)
    ).count()
    if so_phien >= SO_PHIEN_MOI_GIO:
        raise ValidationError(
            "Email này đã yêu cầu quá nhiều mã trong một giờ. Vui lòng thử lại sau."
        )
    ma_otp = _tao_otp()
    ma_phien = tao_ma_uuid()
    phien = PhienXacThuc.objects.create(
        ma_phien_xac_thuc=ma_phien,
        loai_xac_thuc=loai,
        email=email,
        tai_khoan=tai_khoan,
        bam_otp=_bam(ma_phien, ma_otp),
        thoi_diem_gui_cuoi=bay_gio,
        thoi_diem_het_han=bay_gio + timedelta(minutes=PhienXacThuc.SO_PHUT_HIEU_LUC),
        **dang_ky,
    )
    if gui:
        _gui_ma(phien, ma_otp, ho_ten)
    return phien


def _kiem_trung(ten_dang_nhap=None, email=None, tru=None):
    tai_khoan = get_user_model().objects.exclude(pk=getattr(tru, "pk", None))
    if ten_dang_nhap and tai_khoan.filter(ten_dang_nhap=ten_dang_nhap).exists():
        raise ValidationError("Tên đăng nhập đã được sử dụng.")
    if email and tai_khoan.filter(email=email).exists():
        raise ValidationError("Email đã được dùng cho một tài khoản khác.")


def lay_phien(ma_phien, loai):
    """Phiên còn có thể nhập mã, hoặc None nếu không có."""
    return PhienXacThuc.objects.filter(ma_phien_xac_thuc=ma_phien, loai_xac_thuc=loai).first()


def _loi_trang_thai(phien, bay_gio):
    if phien.thoi_diem_su_dung:
        return "Mã này đã được sử dụng."
    if phien.so_lan_nhap_sai >= PhienXacThuc.SO_LAN_NHAP_SAI_TOI_DA:
        return "Bạn đã nhập sai quá 5 lần. Hãy gửi lại mã mới."
    if bay_gio > phien.thoi_diem_het_han:
        return "Mã đã hết hạn. Hãy bấm gửi lại mã."
    return None


def _dung_ma(ma_phien, loai, ma_otp, hanh_dong):
    """Kiểm mã rồi chạy `hanh_dong(phien)` trong cùng transaction.

    Lần nhập sai được ghi trước khi báo lỗi, nên lỗi phải nêu sau khi khối
    atomic đã commit.
    """
    loi = None
    with transaction.atomic():
        phien = (
            PhienXacThuc.objects.select_for_update()
            .filter(ma_phien_xac_thuc=ma_phien, loai_xac_thuc=loai)
            .first()
        )
        if phien is None:
            raise ValidationError("Phiên xác thực không tồn tại.")
        bay_gio = timezone.now()
        loi = _loi_trang_thai(phien, bay_gio)
        if not loi and not hmac.compare_digest(_bam(ma_phien, ma_otp), phien.bam_otp):
            phien.so_lan_nhap_sai += 1
            phien.save(update_fields=["so_lan_nhap_sai"])
            con_lai = PhienXacThuc.SO_LAN_NHAP_SAI_TOI_DA - phien.so_lan_nhap_sai
            loi = (
                f"Mã không đúng. Bạn còn {con_lai} lần thử."
                if con_lai
                else "Mã không đúng. Phiên đã bị khóa, hãy gửi lại mã mới."
            )
        if not loi:
            ket_qua = hanh_dong(phien)
            phien.thoi_diem_su_dung = bay_gio
            phien.save(update_fields=["thoi_diem_su_dung"])
    if loi:
        raise ValidationError(loi)
    return ket_qua


def gui_lai_ma(ma_phien, loai):
    with transaction.atomic():
        phien = (
            PhienXacThuc.objects.select_for_update(of=("self",))
            .select_related("tai_khoan")
            .filter(ma_phien_xac_thuc=ma_phien, loai_xac_thuc=loai)
            .first()
        )
        if phien is None:
            raise ValidationError("Phiên xác thực không tồn tại.")
        bay_gio = timezone.now()
        if phien.thoi_diem_su_dung:
            raise ValidationError("Mã này đã được sử dụng.")
        cho = GIAY_CHO_GUI_LAI - int((bay_gio - phien.thoi_diem_gui_cuoi).total_seconds())
        if cho > 0:
            raise ValidationError(f"Vui lòng đợi {cho} giây trước khi gửi lại mã.")
        if phien.so_lan_gui >= PhienXacThuc.SO_LAN_GUI_TOI_DA:
            raise ValidationError("Đã gửi lại mã tối đa 5 lần. Hãy bắt đầu lại từ đầu.")
        ma_otp = _tao_otp()
        phien.bam_otp = _bam(ma_phien, ma_otp)
        phien.so_lan_gui += 1
        phien.so_lan_nhap_sai = 0
        phien.thoi_diem_gui_cuoi = bay_gio
        phien.thoi_diem_het_han = bay_gio + timedelta(minutes=PhienXacThuc.SO_PHUT_HIEU_LUC)
        phien.save(
            update_fields=[
                "bam_otp",
                "so_lan_gui",
                "so_lan_nhap_sai",
                "thoi_diem_gui_cuoi",
                "thoi_diem_het_han",
            ]
        )
        # Phiên quên mật khẩu với email lạ không gửi gì để không lộ email đã đăng ký.
        if loai != "quen_mat_khau" or phien.tai_khoan_id:
            ho_ten = phien.ho_ten_dang_ky or getattr(phien.tai_khoan, "ho_ten", "")
            _gui_ma(phien, ma_otp, ho_ten)
    return phien


# Đăng ký


@transaction.atomic
def bat_dau_dang_ky(*, ho_ten, email, so_dien_thoai, ten_dang_nhap, mat_khau):
    _kiem_trung(ten_dang_nhap=ten_dang_nhap, email=email)
    nhap = get_user_model()(ten_dang_nhap=ten_dang_nhap, email=email, ho_ten=ho_ten)
    validate_password(mat_khau, nhap)
    return _tao_phien(
        "dang_ky",
        email,
        ho_ten=ho_ten,
        ho_ten_dang_ky=ho_ten,
        ten_dang_nhap_dang_ky=ten_dang_nhap,
        so_dien_thoai_dang_ky=so_dien_thoai,
        mat_khau_bam_dang_ky=make_password(mat_khau),
    )


def hoan_tat_dang_ky(ma_phien, ma_otp):
    def tao_tai_khoan(phien):
        _kiem_trung(ten_dang_nhap=phien.ten_dang_nhap_dang_ky, email=phien.email)
        tai_khoan = get_user_model()(
            ten_dang_nhap=phien.ten_dang_nhap_dang_ky,
            password=phien.mat_khau_bam_dang_ky,
            ho_ten=phien.ho_ten_dang_ky,
            email=phien.email,
            so_dien_thoai=phien.so_dien_thoai_dang_ky,
            da_xac_thuc_email=True,
            vai_tro="khach_hang",
        )
        try:
            with transaction.atomic():
                tai_khoan.save()
        except IntegrityError as loi:
            raise ValidationError("Tên đăng nhập hoặc email vừa được người khác dùng.") from loi
        gui_email(
            loai_email="chao_mung",
            email_nhan=tai_khoan.email,
            tai_khoan=tai_khoan,
            tieu_de=f"Chào mừng bạn đến với {ten_thuong_hieu()}",
            mau="chao_mung",
            ngu_canh={"ho_ten": tai_khoan.ho_ten, "ten_dang_nhap": tai_khoan.ten_dang_nhap},
        )
        return tai_khoan

    return _dung_ma(ma_phien, "dang_ky", ma_otp, tao_tai_khoan)


# Quên mật khẩu


@transaction.atomic
def bat_dau_quen_mat_khau(email):
    """Luôn tạo phiên để trang phản hồi giống nhau dù email có tài khoản hay không."""
    tai_khoan = get_user_model().objects.filter(email=email, dang_hoat_dong=True).first()
    return _tao_phien(
        "quen_mat_khau",
        email,
        tai_khoan=tai_khoan,
        gui=tai_khoan is not None,
        ho_ten=getattr(tai_khoan, "ho_ten", ""),
    )


def dat_lai_mat_khau(ma_phien, ma_otp, mat_khau_moi):
    def doi(phien):
        if phien.tai_khoan_id is None:
            raise ValidationError("Phiên xác thực không hợp lệ.")
        tai_khoan = get_user_model().objects.select_for_update().get(pk=phien.tai_khoan_id)
        if tai_khoan.email != phien.email or not tai_khoan.dang_hoat_dong:
            raise ValidationError("Tài khoản đã thay đổi email hoặc bị khóa, hãy yêu cầu lại.")
        validate_password(mat_khau_moi, tai_khoan)
        tai_khoan.set_password(mat_khau_moi)
        tai_khoan.da_xac_thuc_email = True
        tai_khoan.save(update_fields=["password", "da_xac_thuc_email"])
        bao_doi_mat_khau(tai_khoan, "đặt lại bằng mã xác thực email")
        return tai_khoan

    return _dung_ma(ma_phien, "quen_mat_khau", ma_otp, doi)


def bao_doi_mat_khau(tai_khoan, cach_doi):
    if tai_khoan.email:
        gui_email(
            loai_email="mat_khau_da_doi",
            email_nhan=tai_khoan.email,
            tai_khoan=tai_khoan,
            tieu_de="Mật khẩu tài khoản vừa được thay đổi",
            mau="mat_khau_da_doi",
            ngu_canh={
                "ho_ten": tai_khoan.ho_ten,
                "ten_dang_nhap": tai_khoan.ten_dang_nhap,
                "cach_doi": cach_doi,
                "thoi_diem": timezone.localtime(),
            },
        )


# Đổi email


@transaction.atomic
def bat_dau_doi_email(nguoi, email_moi, mat_khau_hien_tai):
    if not nguoi.check_password(mat_khau_hien_tai):
        raise ValidationError("Mật khẩu hiện tại không đúng.")
    if email_moi == nguoi.email:
        raise ValidationError("Email mới trùng email hiện tại.")
    _kiem_trung(email=email_moi, tru=nguoi)
    return _tao_phien("doi_email", email_moi, tai_khoan=nguoi, ho_ten=nguoi.ho_ten)


def che_email(email):
    ten, _, mien = email.partition("@")
    return f"{ten[:2]}{'*' * max(len(ten) - 2, 1)}@{mien}"


def xac_nhan_doi_email(nguoi, ma_phien, ma_otp):
    phien = lay_phien(ma_phien, "doi_email")
    if phien is None or phien.tai_khoan_id != nguoi.pk:
        raise ValidationError("Phiên xác thực không tồn tại.")

    def doi(phien):
        tai_khoan = get_user_model().objects.select_for_update().get(pk=nguoi.pk)
        email_cu = tai_khoan.email
        _kiem_trung(email=phien.email, tru=tai_khoan)
        tai_khoan.email = phien.email
        tai_khoan.da_xac_thuc_email = True
        try:
            with transaction.atomic():
                tai_khoan.save(update_fields=["email", "da_xac_thuc_email"])
        except IntegrityError as loi:
            raise ValidationError("Email vừa được dùng cho tài khoản khác.") from loi
        if email_cu:
            gui_email(
                loai_email="email_da_doi",
                email_nhan=email_cu,
                tai_khoan=tai_khoan,
                tieu_de="Email tài khoản vừa được thay đổi",
                mau="email_da_doi",
                ngu_canh={
                    "ho_ten": tai_khoan.ho_ten,
                    "ten_dang_nhap": tai_khoan.ten_dang_nhap,
                    "email_moi_che": che_email(tai_khoan.email),
                    "thoi_diem": timezone.localtime(),
                },
            )
        return tai_khoan

    return _dung_ma(ma_phien, "doi_email", ma_otp, doi)


# Nhắc tên đăng nhập


@transaction.atomic
def nhac_ten_dang_nhap(email):
    """Gửi tên đăng nhập nếu email thuộc tài khoản đang hoạt động; không báo kết quả."""
    from ung_dung.thong_bao.models import NhatKyEmail

    tai_khoan = get_user_model().objects.filter(email=email, dang_hoat_dong=True).first()
    if tai_khoan is None:
        return
    da_gui = NhatKyEmail.objects.filter(
        loai_email="nhac_ten_dang_nhap",
        email_nhan=email,
        thoi_diem_tao__gte=timezone.now() - timedelta(hours=1),
    ).count()
    if da_gui >= SO_NHAC_TEN_MOI_GIO:
        return
    gui_email(
        loai_email="nhac_ten_dang_nhap",
        email_nhan=email,
        tai_khoan=tai_khoan,
        tieu_de="Tên đăng nhập của bạn",
        mau="nhac_ten_dang_nhap",
        ngu_canh={"ten_dang_nhap": tai_khoan.ten_dang_nhap},
    )
