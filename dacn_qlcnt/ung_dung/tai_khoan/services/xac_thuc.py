"""Mã OTP qua email cho đăng ký, quên mật khẩu, đổi email và nhắc tên đăng nhập.

Mã sáu chữ số chỉ tồn tại trong bộ nhớ khi gửi; CSDL giữ HMAC-SHA256 của
"ma_phien:ma_otp" với khóa SECRET_KEY. Mỗi phiên hết hạn sau 10 phút, khóa sau
5 lần nhập sai, gửi lại tối đa 5 lần và cách nhau ít nhất 60 giây. Mỗi email chỉ
được mở 5 phiên mỗi giờ, mỗi địa chỉ IP 10 phiên mỗi giờ; toàn hệ thống có trần số thư mã
mỗi ngày để không dùng hết hạn mức gửi của Gmail (thư đơn hàng dùng chung tài khoản gửi).

Không để lộ email nào đã có tài khoản: quên mật khẩu gửi mã nền (thời gian phản hồi như
nhau), đăng ký bằng email đã có tài khoản vẫn chuyển sang trang nhập mã nhưng chủ email
nhận thư báo "email này đã có tài khoản" thay vì mã.
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

from ung_dung.thong_bao.services import gui_email, ten_thuong_hieu, url_tuyet_doi

from ..models import PhienXacThuc, tao_ma_uuid

GIAY_CHO_GUI_LAI = 60
SO_PHIEN_MOI_GIO = 5
SO_PHIEN_MOI_GIO_MOI_IP = 10
# Gmail cá nhân chặn tài khoản gửi quá khoảng 500 thư/ngày; chừa phần còn lại cho thư đơn hàng.
SO_THU_MA_MOI_NGAY = getattr(settings, "SO_THU_MA_XAC_THUC_MOI_NGAY", 300)
SO_NHAC_TEN_MOI_GIO = 3
MUC_DICH = {
    "dang_ky": "hoàn tất đăng ký tài khoản",
    "quen_mat_khau": "đặt lại mật khẩu",
    "doi_email": "xác nhận email mới",
}
TIEU_DE_MA = {
    "dang_ky": "Mã xác thực đăng ký tài khoản",
    "quen_mat_khau": "Mã đặt lại mật khẩu",
    "doi_email": "Mã xác nhận email mới",
}
# Thư gửi khi có người yêu cầu mã; tính chung vào trần mỗi ngày.
LOAI_THU_MA = ("ma_xac_thuc", "email_da_co_tai_khoan")


def _bam(ma_phien, ma_otp):
    return hmac.new(
        settings.SECRET_KEY.encode(), f"{ma_phien}:{ma_otp}".encode(), hashlib.sha256
    ).hexdigest()


def _tao_otp():
    return f"{secrets.randbelow(10**6):06d}"


def _nut(nhan, ten_url, *args):
    return {"nhan": nhan, "url": url_tuyet_doi(ten_url, *args)}


def _gui_ma(phien, ma_otp, ho_ten=""):
    gui_email(
        loai_email="ma_xac_thuc",
        email_nhan=phien.email,
        tai_khoan=phien.tai_khoan,
        tieu_de=TIEU_DE_MA[phien.loai_xac_thuc],
        tom_tat=f"Mã có hiệu lực {PhienXacThuc.SO_PHUT_HIEU_LUC} phút và chỉ dùng một lần.",
        mau="ma_xac_thuc",
        # Đăng ký, đổi email: gửi ngay để trang nhập mã báo đúng khi thư không đi được.
        # Quên mật khẩu: gửi nền để thời gian phản hồi như nhau dù email có tài khoản hay
        # không (trang đó cũng không báo kết quả gửi).
        gui_ngay=phien.loai_xac_thuc != "quen_mat_khau",
        ngu_canh={
            "ho_ten": ho_ten,
            "ma_otp": ma_otp,
            "muc_dich": MUC_DICH[phien.loai_xac_thuc],
            "so_phut": PhienXacThuc.SO_PHUT_HIEU_LUC,
            "het_han": timezone.localtime(phien.thoi_diem_het_han),
        },
    )


def _bao_email_da_co_tai_khoan(phien, tai_khoan):
    """Đăng ký bằng email đã có tài khoản: báo chủ email thay vì báo lỗi trên trang."""
    gui_email(
        loai_email="email_da_co_tai_khoan",
        email_nhan=phien.email,
        tai_khoan=tai_khoan,
        tieu_de="Email của bạn đã có tài khoản",
        tom_tat="Có người vừa dùng email này để đăng ký. Bạn đăng nhập bằng tài khoản sẵn có.",
        mau="email_da_co_tai_khoan",
        gui_ngay=True,
        ngu_canh={
            "ten_dang_nhap": tai_khoan.ten_dang_nhap,
            "thoi_diem": timezone.localtime(),
            "nut_chinh": _nut("Đăng nhập", "tai_khoan:dang_nhap"),
            "nut_phu": _nut("Quên mật khẩu", "tai_khoan:quen_mat_khau"),
        },
    )


def ket_qua_gui_ma(phien):
    """Trạng thái thư của lần gửi gần nhất: 'da_gui', 'loi', 'cho_gui' hoặc None khi
    không gửi (quên mật khẩu với email không có tài khoản)."""
    from ung_dung.thong_bao.models import NhatKyEmail

    thu = (
        NhatKyEmail.objects.filter(
            loai_email__in=LOAI_THU_MA,
            email_nhan=phien.email,
            thoi_diem_tao__gte=phien.thoi_diem_gui_cuoi - timedelta(seconds=30),
        )
        .order_by("-pk")
        .first()
    )
    return thu.trang_thai if thu else None


def _kiem_gioi_han(email, dia_chi_ip, bay_gio):
    """Chặn gửi mã quá nhiều: theo email và theo IP trong một giờ, trần thư mã mỗi ngày."""
    from ung_dung.thong_bao.models import NhatKyEmail

    mot_gio_truoc = bay_gio - timedelta(hours=1)
    trong_gio = PhienXacThuc.objects.filter(thoi_diem_tao__gte=mot_gio_truoc)
    if trong_gio.filter(email=email).count() >= SO_PHIEN_MOI_GIO:
        raise ValidationError(
            "Email này đã yêu cầu quá nhiều mã trong một giờ. Vui lòng thử lại sau."
        )
    if dia_chi_ip and trong_gio.filter(dia_chi_ip=dia_chi_ip).count() >= SO_PHIEN_MOI_GIO_MOI_IP:
        raise ValidationError(
            "Bạn đã yêu cầu quá nhiều mã xác thực trong một giờ. Vui lòng thử lại sau."
        )
    dau_ngay = timezone.localtime(bay_gio).replace(hour=0, minute=0, second=0, microsecond=0)
    so_thu_hom_nay = NhatKyEmail.objects.filter(
        loai_email__in=LOAI_THU_MA, thoi_diem_tao__gte=dau_ngay
    ).count()
    if so_thu_hom_nay >= SO_THU_MA_MOI_NGAY:
        raise ValidationError(
            "Hôm nay hệ thống đã gửi quá nhiều mã xác thực nên tạm dừng để bảo vệ hộp thư. "
            "Vui lòng thử lại vào ngày mai hoặc gọi nhà thuốc để được hỗ trợ."
        )


def _tao_phien(loai, email, *, tai_khoan=None, gui=True, ho_ten="", dia_chi_ip=None, **dang_ky):
    bay_gio = timezone.now()
    _kiem_gioi_han(email, dia_chi_ip, bay_gio)
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
        dia_chi_ip=dia_chi_ip,
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
        # Phiên quên mật khẩu với email lạ không gửi gì để không lộ email đã đăng ký; phiên
        # đăng ký bằng email đã có tài khoản gửi lại thư báo thay vì mã.
        if loai == "dang_ky" and (
            chu_email := get_user_model().objects.filter(email=phien.email).first()
        ):
            _bao_email_da_co_tai_khoan(phien, chu_email)
        elif loai != "quen_mat_khau" or phien.tai_khoan_id:
            ho_ten = phien.ho_ten_dang_ky or getattr(phien.tai_khoan, "ho_ten", "")
            _gui_ma(phien, ma_otp, ho_ten)
    return phien


# Đăng ký


@transaction.atomic
def bat_dau_dang_ky(*, ho_ten, email, so_dien_thoai, ten_dang_nhap, mat_khau, dia_chi_ip=None):
    """Mở phiên đăng ký và gửi mã. Email đã có tài khoản thì trang phản hồi y hệt, nhưng chủ
    email nhận thư báo thay vì mã, nên không ai dò được email nào đã đăng ký."""
    _kiem_trung(ten_dang_nhap=ten_dang_nhap)
    nhap = get_user_model()(ten_dang_nhap=ten_dang_nhap, email=email, ho_ten=ho_ten)
    validate_password(mat_khau, nhap)
    chu_email = get_user_model().objects.filter(email=email).first()
    phien = _tao_phien(
        "dang_ky",
        email,
        gui=chu_email is None,
        ho_ten=ho_ten,
        dia_chi_ip=dia_chi_ip,
        ho_ten_dang_ky=ho_ten,
        ten_dang_nhap_dang_ky=ten_dang_nhap,
        so_dien_thoai_dang_ky=so_dien_thoai,
        mat_khau_bam_dang_ky=make_password(mat_khau),
    )
    if chu_email is not None:
        _bao_email_da_co_tai_khoan(phien, chu_email)
    return phien


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
            tom_tat="Tài khoản đã sẵn sàng: tra cứu thuốc, đặt giữ, đặt giao và theo dõi đơn.",
            mau="chao_mung",
            ngu_canh={
                "ho_ten": tai_khoan.ho_ten,
                "ten_dang_nhap": tai_khoan.ten_dang_nhap,
                "nut_chinh": _nut("Mở tài khoản của tôi", "tai_khoan:cua_toi"),
                "nut_phu": _nut("Tìm thuốc", "danh_muc:khach_thuoc_danh_sach"),
            },
        )
        return tai_khoan

    return _dung_ma(ma_phien, "dang_ky", ma_otp, tao_tai_khoan)


# Quên mật khẩu


@transaction.atomic
def bat_dau_quen_mat_khau(email, dia_chi_ip=None):
    """Luôn tạo phiên để trang phản hồi giống nhau dù email có tài khoản hay không."""
    tai_khoan = get_user_model().objects.filter(email=email, dang_hoat_dong=True).first()
    return _tao_phien(
        "quen_mat_khau",
        email,
        tai_khoan=tai_khoan,
        gui=tai_khoan is not None,
        ho_ten=getattr(tai_khoan, "ho_ten", ""),
        dia_chi_ip=dia_chi_ip,
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
        # Chủ tài khoản đã chứng minh qua email nên mở khóa đăng nhập do nhập sai.
        tai_khoan.so_lan_dang_nhap_sai = 0
        tai_khoan.thoi_diem_mo_khoa_dang_nhap = None
        tai_khoan.save(
            update_fields=[
                "password",
                "da_xac_thuc_email",
                "so_lan_dang_nhap_sai",
                "thoi_diem_mo_khoa_dang_nhap",
            ]
        )
        bao_doi_mat_khau(tai_khoan, "đặt lại bằng mã xác thực email")
        return tai_khoan

    return _dung_ma(ma_phien, "quen_mat_khau", ma_otp, doi)


def bao_doi_mat_khau(tai_khoan, cach_doi, *, boi_quan_tri=False):
    if tai_khoan.email:
        gui_email(
            loai_email="mat_khau_da_doi",
            email_nhan=tai_khoan.email,
            tai_khoan=tai_khoan,
            tieu_de="Mật khẩu tài khoản vừa được thay đổi",
            tom_tat="Không phải bạn? Đặt lại mật khẩu ngay và gọi nhà thuốc.",
            mau="mat_khau_da_doi",
            ngu_canh={
                "ho_ten": tai_khoan.ho_ten,
                "ten_dang_nhap": tai_khoan.ten_dang_nhap,
                "cach_doi": cach_doi,
                "boi_quan_tri": boi_quan_tri,
                "thoi_diem": timezone.localtime(),
                "nut_chinh": _nut("Đăng nhập", "tai_khoan:dang_nhap"),
            },
        )


def bao_email_da_doi(tai_khoan, email_cu, *, boi_quan_tri=False):
    """Báo email cũ khi email tài khoản đổi. Người dùng tự đổi thì kèm liên kết khôi phục email
    cũ (7 ngày); quản trị đổi thì nhắc gọi hotline."""
    url_hoan_tac = "" if boi_quan_tri else tao_lien_ket_hoan_tac_email(tai_khoan, email_cu)
    gui_email(
        loai_email="email_da_doi",
        email_nhan=email_cu,
        tai_khoan=tai_khoan,
        tieu_de="Email tài khoản vừa được thay đổi",
        tom_tat="Không phải bạn đổi? Khôi phục email cũ hoặc gọi nhà thuốc ngay.",
        mau="email_da_doi",
        ngu_canh={
            "ho_ten": tai_khoan.ho_ten,
            "ten_dang_nhap": tai_khoan.ten_dang_nhap,
            "email_moi_che": che_email(tai_khoan.email) if tai_khoan.email else "(để trống)",
            "thoi_diem": timezone.localtime(),
            "boi_quan_tri": boi_quan_tri,
            "url_hoan_tac": url_hoan_tac,
            "so_ngay_hoan_tac": PhienXacThuc.SO_NGAY_HOAN_TAC_EMAIL,
            "nut_chinh": (
                {"nhan": "Không phải tôi – khôi phục email cũ", "url": url_hoan_tac}
                if url_hoan_tac
                else None
            ),
        },
    )


# Đổi email


@transaction.atomic
def bat_dau_doi_email(nguoi, email_moi, mat_khau_hien_tai, dia_chi_ip=None):
    if not nguoi.check_password(mat_khau_hien_tai):
        raise ValidationError("Mật khẩu hiện tại không đúng.")
    if email_moi == nguoi.email:
        raise ValidationError("Email mới trùng email hiện tại.")
    _kiem_trung(email=email_moi, tru=nguoi)
    return _tao_phien(
        "doi_email", email_moi, tai_khoan=nguoi, ho_ten=nguoi.ho_ten, dia_chi_ip=dia_chi_ip
    )


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
            bao_email_da_doi(tai_khoan, email_cu)
        gui_email(
            loai_email="ho_so_da_doi",
            email_nhan=tai_khoan.email,
            tai_khoan=tai_khoan,
            tieu_de="Email mới đã được xác thực",
            mau="ho_so_da_doi",
            ngu_canh={
                "ho_ten": tai_khoan.ho_ten,
                "ten_dang_nhap": tai_khoan.ten_dang_nhap,
                "cac_muc_doi": ["email đăng nhập"],
                "thoi_diem": timezone.localtime(),
                "nut_chinh": _nut("Xem hồ sơ", "tai_khoan:thong_tin"),
            },
        )
        return tai_khoan

    return _dung_ma(ma_phien, "doi_email", ma_otp, doi)


# Khôi phục email cũ: liên kết trong thư gửi email cũ khi email bị đổi.


def tao_lien_ket_hoan_tac_email(tai_khoan, email_cu):
    """Tạo phiên khôi phục email cũ, trả đường dẫn tuyệt đối đặt trong thư gửi email cũ.

    Khóa trên đường dẫn là chuỗi ngẫu nhiên 256 bit; CSDL chỉ giữ HMAC của nó.
    """
    bay_gio = timezone.now()
    ma_phien, khoa = tao_ma_uuid(), secrets.token_urlsafe(32)
    PhienXacThuc.objects.create(
        ma_phien_xac_thuc=ma_phien,
        loai_xac_thuc="hoan_tac_email",
        email=email_cu,
        tai_khoan=tai_khoan,
        bam_otp=_bam(ma_phien, f"{khoa}:{tai_khoan.email}"),
        thoi_diem_gui_cuoi=bay_gio,
        thoi_diem_het_han=bay_gio + timedelta(days=PhienXacThuc.SO_NGAY_HOAN_TAC_EMAIL),
    )
    return url_tuyet_doi("tai_khoan:hoan_tac_doi_email", ma_phien, khoa)


def kiem_lien_ket_hoan_tac(ma_phien, khoa):
    """Phiên khôi phục còn dùng được; ValidationError kèm lời giải thích nếu không."""
    phien = lay_phien(str(ma_phien), "hoan_tac_email")
    if phien is None or not _lien_ket_dung_tai_khoan(phien, khoa, phien.tai_khoan):
        raise ValidationError("Liên kết khôi phục không đúng. Hãy mở lại liên kết trong email.")
    if phien.thoi_diem_su_dung:
        raise ValidationError("Liên kết này đã được dùng để khôi phục email.")
    if timezone.now() > phien.thoi_diem_het_han:
        raise ValidationError(
            "Liên kết khôi phục đã hết hạn. Hãy gọi nhà thuốc để được hỗ trợ lấy lại tài khoản."
        )
    return phien


def _lien_ket_dung_tai_khoan(phien, khoa, tai_khoan):
    return (
        tai_khoan.email
        and tai_khoan.email != phien.email
        and hmac.compare_digest(
            _bam(str(phien.ma_phien_xac_thuc), f"{khoa}:{tai_khoan.email}"), phien.bam_otp
        )
        and not PhienXacThuc.objects.filter(
            loai_xac_thuc="hoan_tac_email",
            tai_khoan=tai_khoan,
            pk__gt=phien.pk,
        ).exists()
    )


@transaction.atomic
def hoan_tac_doi_email(ma_phien, khoa):
    """Đưa tài khoản về email cũ và vô hiệu mật khẩu (mọi phiên đăng nhập bị thoát) để chủ
    tài khoản đặt mật khẩu mới qua email cũ. Trả tài khoản đã khôi phục."""
    phien = kiem_lien_ket_hoan_tac(ma_phien, khoa)
    phien = PhienXacThuc.objects.select_for_update().get(pk=phien.pk)
    if phien.thoi_diem_su_dung:
        raise ValidationError("Liên kết này đã được dùng để khôi phục email.")
    tai_khoan = get_user_model().objects.select_for_update().get(pk=phien.tai_khoan_id)
    if not _lien_ket_dung_tai_khoan(phien, khoa, tai_khoan):
        raise ValidationError("Liên kết đã hết hiệu lực vì email của tài khoản đã đổi.")
    if tai_khoan.email != phien.email:
        if get_user_model().objects.filter(email=phien.email).exclude(pk=tai_khoan.pk).exists():
            raise ValidationError(
                "Email cũ đã được dùng cho tài khoản khác. Hãy gọi nhà thuốc để được hỗ trợ."
            )
        tai_khoan.email = phien.email
    tai_khoan.da_xac_thuc_email = True
    tai_khoan.set_unusable_password()
    tai_khoan.save(update_fields=["email", "da_xac_thuc_email", "password"])
    phien.thoi_diem_su_dung = timezone.now()
    phien.save(update_fields=["thoi_diem_su_dung"])
    return tai_khoan


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
        tom_tat="Tên đăng nhập bạn vừa yêu cầu nhắc lại.",
        mau="nhac_ten_dang_nhap",
        ngu_canh={
            "ten_dang_nhap": tai_khoan.ten_dang_nhap,
            "nut_chinh": _nut("Đăng nhập", "tai_khoan:dang_nhap"),
            "nut_phu": _nut("Quên mật khẩu", "tai_khoan:quen_mat_khau"),
        },
    )
