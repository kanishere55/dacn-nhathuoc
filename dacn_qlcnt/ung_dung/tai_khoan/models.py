import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.gis.db.models import PointField
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now

from ung_dung.chung.ten_csdl import (
    EMAIL,
    MA_UUID,
    SO_DIEN_THOAI,
    rang_buoc_van_ban,
    ten_rang_buoc,
)
from ung_dung.chung.van_ban import DaCatKhoangTrang, KhongRong, LaMotDong

from .managers import QuanLyTaiKhoan


class TaiKhoan(AbstractBaseUser):
    # Các thuộc tính password/last_login giữ giao diện mà Django auth cần.
    id_tai_khoan = models.BigAutoField(
        primary_key=True,
        db_column="id_tai_khoan",
        db_comment="Định danh nội bộ do PostgreSQL cấp, không phải mã hiển thị.",
    )
    ten_dang_nhap = models.TextField(
        "tên đăng nhập",
        db_column="ten_dang_nhap",
        db_comment=("Tên một dòng người tạo nhập, duy nhất và phân biệt hoa thường theo Q10."),
    )
    password = models.CharField(
        "mật khẩu băm",
        max_length=128,
        db_column="mat_khau_bam",
        db_comment=(
            "Chuỗi băm hoặc dấu mật khẩu không sử dụng được do Django tạo; "
            "một dòng, giới hạn 128 ký tự theo AbstractBaseUser.password của Django."
        ),
    )
    dang_hoat_dong = models.BooleanField(
        "đang hoạt động",
        db_default=True,
        db_column="dang_hoat_dong",
        db_comment="Cho phép cơ chế xác thực Django nhận tài khoản; hệ thống ghi.",
    )
    la_quan_tri_he_thong = models.BooleanField(
        "là quản trị hệ thống",
        db_default=False,
        db_column="la_quan_tri_he_thong",
        db_comment=(
            "Cờ quản trị kỹ thuật của Django tạo bằng createsuperuser, chỉ cấp cho quản trị chuỗi."
        ),
    )
    last_login = models.DateTimeField(
        "thời điểm đăng nhập cuối",
        null=True,
        blank=True,
        db_column="thoi_diem_dang_nhap_cuoi",
        db_comment=(
            "Thời điểm đăng nhập thành công gần nhất do Django cập nhật; "
            "NULL nghĩa là chưa ghi nhận lần đăng nhập."
        ),
    )

    class VaiTro(models.TextChoices):
        QUAN_TRI = "quan_tri_chuoi", "Quản trị chuỗi"
        QUAN_LY = "quan_ly_chi_nhanh", "Quản lý chi nhánh"
        NHAN_VIEN = "nhan_vien", "Nhân viên"
        KHACH_HANG = "khach_hang", "Khách hàng"

    vai_tro = models.TextField(
        choices=VaiTro.choices,
        db_default="khach_hang",
        db_column="vai_tro",
        db_comment="Vai trò nghiệp vụ do quản trị cấp; quan_tri_chuoi quản lý chuỗi, quan_ly_chi_nhanh quản lý cơ sở, nhan_vien làm việc tại cơ sở, khach_hang đặt giữ và chat.",
    )
    chi_nhanh = models.ForeignKey(
        "danh_muc.ChiNhanh",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="id_chi_nhanh",
        db_comment="Chi nhánh làm việc của quản lý/nhân viên; NULL với khách và quản trị chuỗi.",
    )
    ho_ten = models.TextField(
        "họ tên",
        blank=True,
        db_default="",
        db_column="ho_ten",
        db_comment="Họ tên người dùng tự khai hoặc quản trị nhập; văn bản một dòng, rỗng khi chưa khai.",
    )
    email = models.TextField(
        "email",
        null=True,
        blank=True,
        db_column="email",
        db_comment="Email đã chuẩn hóa chữ thường, duy nhất toàn hệ thống; NULL khi chưa khai báo.",
    )
    so_dien_thoai = models.TextField(
        "số điện thoại",
        blank=True,
        db_default="",
        db_column="so_dien_thoai",
        db_comment="Số điện thoại Việt Nam dạng nội địa 10 hoặc 11 chữ số; rỗng khi chưa khai.",
    )
    da_xac_thuc_email = models.BooleanField(
        "đã xác thực email",
        db_default=False,
        db_column="da_xac_thuc_email",
        db_comment="Người dùng đã nhập đúng mã OTP gửi tới email hiện tại.",
    )
    dia_chi_giao_hang_mac_dinh = models.ForeignKey(
        "tai_khoan.DiaChiGiaoHang",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="id_dia_chi_giao_hang_mac_dinh",
        db_comment=(
            "Địa chỉ chọn sẵn khi đặt giao hàng; service chỉ cho trỏ tới địa chỉ "
            "của chính tài khoản. NULL khi chưa chọn."
        ),
    )
    thoi_diem_tao = models.DateTimeField(
        "thời điểm tạo",
        db_default=Now(),
        db_column="thoi_diem_tao",
        db_comment="Thời điểm tài khoản được tạo.",
    )

    objects = QuanLyTaiKhoan()
    USERNAME_FIELD = "ten_dang_nhap"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "tai_khoan"
        db_table_comment = "Mỗi hàng là một tài khoản xác thực có một vai trò nghiệp vụ."
        verbose_name = "tài khoản"
        verbose_name_plural = "tài khoản"
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    vai_tro__in=["quan_tri_chuoi", "quan_ly_chi_nhanh", "nhan_vien", "khach_hang"]
                ),
                name="kiem_tra__tai_khoan__vai_tro_hop_le",
            ),
            models.CheckConstraint(
                condition=(
                    Q(vai_tro__in=["quan_ly_chi_nhanh", "nhan_vien"], chi_nhanh__isnull=False)
                    | Q(vai_tro__in=["quan_tri_chuoi", "khach_hang"], chi_nhanh__isnull=True)
                ),
                name="kiem_tra__tai_khoan__chi_nhanh_dung_vai_tro",
            ),
            models.CheckConstraint(
                condition=Q(la_quan_tri_he_thong=False) | Q(vai_tro="quan_tri_chuoi"),
                name="kiem_tra__tai_khoan__quan_tri_he_thong_dung_vai_tro",
                violation_error_message="Tài khoản quản trị hệ thống phải có vai trò quản trị chuỗi.",
            ),
            models.UniqueConstraint(
                fields=["ten_dang_nhap"],
                name="duy_nhat__tai_khoan__ten_dang_nhap",
            ),
            models.CheckConstraint(
                condition=KhongRong("ten_dang_nhap"),
                name="kiem_tra__tai_khoan__ten_dang_nhap_khong_rong",
            ),
            models.CheckConstraint(
                condition=DaCatKhoangTrang("ten_dang_nhap"),
                name="kiem_tra__tai_khoan__ten_dang_nhap_da_cat_khoang_trang",
            ),
            models.CheckConstraint(
                condition=LaMotDong("ten_dang_nhap"),
                name="kiem_tra__tai_khoan__ten_dang_nhap_mot_dong",
            ),
            models.CheckConstraint(
                condition=KhongRong("password"),
                name="kiem_tra__tai_khoan__mat_khau_bam_khong_rong",
            ),
            models.CheckConstraint(
                condition=DaCatKhoangTrang("password"),
                name="kiem_tra__tai_khoan__mat_khau_bam_da_cat_khoang_trang",
            ),
            models.CheckConstraint(
                condition=LaMotDong("password"),
                name="kiem_tra__tai_khoan__mat_khau_bam_mot_dong",
            ),
            *rang_buoc_van_ban("tai_khoan", "ho_ten", rong=True),
            *rang_buoc_van_ban("tai_khoan", "email", dinh_dang=EMAIL),
            *rang_buoc_van_ban(
                "tai_khoan", "so_dien_thoai", rong=True, dinh_dang=f"^({SO_DIEN_THOAI[1:-1]})?$"
            ),
            models.UniqueConstraint(fields=["email"], name="duy_nhat__tai_khoan__email"),
            models.CheckConstraint(
                condition=Q(da_xac_thuc_email=False) | Q(email__isnull=False),
                name="kiem_tra__tai_khoan__xac_thuc_can_email",
            ),
        ]

    @property
    def is_active(self):
        return self.dang_hoat_dong

    @property
    def is_staff(self):
        return self.la_quan_tri_he_thong

    @property
    def is_superuser(self):
        return self.la_quan_tri_he_thong

    def has_perm(self, perm, obj=None):
        return self.dang_hoat_dong and self.la_quan_tri_he_thong

    def has_perms(self, perm_list, obj=None):
        return self.dang_hoat_dong and self.la_quan_tri_he_thong

    def has_module_perms(self, app_label):
        return self.dang_hoat_dong and self.la_quan_tri_he_thong

    def __str__(self):
        return self.ten_dang_nhap


def tao_ma_uuid():
    return str(uuid.uuid4())


class DiaChiGiaoHang(models.Model):
    BANG = "dia_chi_giao_hang"

    id_dia_chi_giao_hang = models.BigAutoField(
        primary_key=True,
        db_column="id_dia_chi_giao_hang",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
    )
    tai_khoan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cac_dia_chi_giao_hang",
        db_column="id_tai_khoan",
        db_comment="Khách sở hữu địa chỉ trong sổ địa chỉ.",
    )
    ten_nguoi_nhan = models.TextField(
        "người nhận",
        db_column="ten_nguoi_nhan",
        db_comment="Họ tên người nhận hàng do khách nhập; văn bản một dòng.",
    )
    so_dien_thoai = models.TextField(
        "số điện thoại",
        db_column="so_dien_thoai",
        db_comment="Số điện thoại người nhận, dạng nội địa 10 hoặc 11 chữ số.",
    )
    dia_chi = models.TextField(
        "địa chỉ",
        db_column="dia_chi",
        db_comment="Địa chỉ giao hàng đầy đủ khách nhập hoặc chọn từ kết quả tìm; một dòng.",
    )
    vi_tri = PointField(
        geography=True,
        srid=4326,
        db_column="vi_tri",
        db_comment="Tọa độ WGS84 khách ghim trên bản đồ; dùng tính quãng đường giao.",
    )
    ghi_chu = models.TextField(
        "ghi chú cho người giao",
        blank=True,
        db_default="",
        db_column="ghi_chu",
        db_comment="Chỉ dẫn thêm như số tầng, cổng; văn bản một dòng, có thể rỗng.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_default=Now(),
        db_column="thoi_diem_tao",
        db_comment="Thời điểm khách thêm địa chỉ.",
    )

    class Meta:
        db_table = "dia_chi_giao_hang"
        db_table_comment = "Mỗi hàng là một địa chỉ nhận hàng trong sổ địa chỉ của khách."
        verbose_name = "địa chỉ giao hàng"
        verbose_name_plural = "địa chỉ giao hàng"
        ordering = ["-thoi_diem_tao", "-id_dia_chi_giao_hang"]
        constraints = [
            *rang_buoc_van_ban("dia_chi_giao_hang", "ten_nguoi_nhan", nhan="ten_nguoi_nhan"),
            *rang_buoc_van_ban("dia_chi_giao_hang", "so_dien_thoai", dinh_dang=SO_DIEN_THOAI),
            *rang_buoc_van_ban("dia_chi_giao_hang", "dia_chi"),
            *rang_buoc_van_ban("dia_chi_giao_hang", "ghi_chu", rong=True),
        ]

    def __str__(self):
        return f"{self.ten_nguoi_nhan} · {self.dia_chi}"


class PhienXacThuc(models.Model):
    """Một lần gửi mã OTP qua email; mã chỉ lưu dạng HMAC-SHA256."""

    BANG = "phien_xac_thuc"
    SO_PHUT_HIEU_LUC = 10
    SO_LAN_NHAP_SAI_TOI_DA = 5
    SO_LAN_GUI_TOI_DA = 5

    class LoaiXacThuc(models.TextChoices):
        DANG_KY = "dang_ky", "Đăng ký tài khoản"
        QUEN_MAT_KHAU = "quen_mat_khau", "Đặt lại mật khẩu"
        DOI_EMAIL = "doi_email", "Đổi email"

    id_phien_xac_thuc = models.BigAutoField(
        primary_key=True,
        db_column="id_phien_xac_thuc",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
    )
    ma_phien_xac_thuc = models.TextField(
        default=tao_ma_uuid,
        db_column="ma_phien_xac_thuc",
        db_comment="UUID ngẫu nhiên đặt trên đường dẫn trang nhập mã; không đoán được.",
    )
    loai_xac_thuc = models.TextField(
        choices=LoaiXacThuc.choices,
        db_column="loai_xac_thuc",
        db_comment="Mục đích của mã: dang_ky, quen_mat_khau hoặc doi_email.",
    )
    email = models.TextField(
        db_column="email",
        db_comment="Email nhận mã, đã chuẩn hóa chữ thường.",
    )
    tai_khoan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="id_tai_khoan",
        db_comment=(
            "Tài khoản được xác thực; NULL khi đăng ký, hoặc khi quên mật khẩu với email "
            "không thuộc tài khoản nào (phiên giả để không lộ email đã đăng ký)."
        ),
    )
    ten_dang_nhap_dang_ky = models.TextField(
        blank=True,
        db_default="",
        db_column="ten_dang_nhap_dang_ky",
        db_comment="Tên đăng nhập chờ tạo khi đăng ký; rỗng với loại khác.",
    )
    ho_ten_dang_ky = models.TextField(
        blank=True,
        db_default="",
        db_column="ho_ten_dang_ky",
        db_comment="Họ tên khai khi đăng ký; rỗng với loại khác.",
    )
    so_dien_thoai_dang_ky = models.TextField(
        blank=True,
        db_default="",
        db_column="so_dien_thoai_dang_ky",
        db_comment="Số điện thoại khai khi đăng ký, có thể rỗng; rỗng với loại khác.",
    )
    mat_khau_bam_dang_ky = models.TextField(
        blank=True,
        db_default="",
        db_column="mat_khau_bam_dang_ky",
        db_comment="Mật khẩu đã băm bằng Django khi đăng ký; rỗng với loại khác.",
    )
    bam_otp = models.TextField(
        db_column="bam_otp",
        db_comment="HMAC-SHA256 hệ thập lục phân của mã OTP sáu chữ số, khóa là SECRET_KEY.",
    )
    so_lan_nhap_sai = models.SmallIntegerField(
        db_default=0,
        db_column="so_lan_nhap_sai",
        db_comment="Số lần nhập sai; đạt 5 thì phiên bị khóa.",
    )
    so_lan_gui = models.SmallIntegerField(
        db_default=1,
        db_column="so_lan_gui",
        db_comment="Số lần đã gửi mã trong phiên, tối đa 5.",
    )
    thoi_diem_gui_cuoi = models.DateTimeField(
        db_column="thoi_diem_gui_cuoi",
        db_comment="Lần gửi mã gần nhất; chặn gửi lại trong 60 giây.",
    )
    thoi_diem_het_han = models.DateTimeField(
        db_column="thoi_diem_het_han",
        db_comment="Sau thời điểm này mã hết hiệu lực, bằng lần gửi cuối cộng 10 phút.",
    )
    thoi_diem_su_dung = models.DateTimeField(
        null=True,
        blank=True,
        db_column="thoi_diem_su_dung",
        db_comment="Thời điểm mã được dùng thành công; NULL khi chưa dùng.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_default=Now(),
        db_column="thoi_diem_tao",
        db_comment="Thời điểm phiên được tạo; dùng giới hạn số phiên mỗi giờ.",
    )

    class Meta:
        db_table = "phien_xac_thuc"
        db_table_comment = "Mỗi hàng là một phiên gửi mã OTP qua email cho một mục đích."
        verbose_name = "phiên xác thực"
        verbose_name_plural = "phiên xác thực"
        indexes = [
            models.Index(
                fields=["email", "thoi_diem_tao"],
                name=ten_rang_buoc("chi_muc", "phien_xac_thuc", "email", "thoi_diem_tao"),
            )
        ]
        constraints = [
            *rang_buoc_van_ban("phien_xac_thuc", "ma_phien_xac_thuc", dinh_dang=MA_UUID),
            models.UniqueConstraint(
                fields=["ma_phien_xac_thuc"],
                name=ten_rang_buoc("duy_nhat", "phien_xac_thuc", "ma_phien_xac_thuc"),
            ),
            models.CheckConstraint(
                condition=Q(loai_xac_thuc__in=["dang_ky", "quen_mat_khau", "doi_email"]),
                name=ten_rang_buoc("kiem_tra", "phien_xac_thuc", "loai_xac_thuc_hop_le"),
            ),
            *rang_buoc_van_ban("phien_xac_thuc", "email", dinh_dang=EMAIL),
            *rang_buoc_van_ban(
                "phien_xac_thuc", "ten_dang_nhap_dang_ky", rong=True, nhan="ten_dang_nhap"
            ),
            *rang_buoc_van_ban("phien_xac_thuc", "ho_ten_dang_ky", rong=True),
            *rang_buoc_van_ban(
                "phien_xac_thuc",
                "so_dien_thoai_dang_ky",
                rong=True,
                dinh_dang=f"^({SO_DIEN_THOAI[1:-1]})?$",
            ),
            *rang_buoc_van_ban("phien_xac_thuc", "mat_khau_bam_dang_ky", rong=True),
            *rang_buoc_van_ban("phien_xac_thuc", "bam_otp", dinh_dang=r"^[0-9a-f]{64}$"),
            models.CheckConstraint(
                condition=(
                    Q(
                        loai_xac_thuc="dang_ky",
                        tai_khoan__isnull=True,
                        ho_ten_dang_ky__gt="",
                        ten_dang_nhap_dang_ky__gt="",
                        mat_khau_bam_dang_ky__gt="",
                    )
                    | (
                        ~Q(loai_xac_thuc="dang_ky")
                        & Q(
                            ten_dang_nhap_dang_ky="",
                            ho_ten_dang_ky="",
                            so_dien_thoai_dang_ky="",
                            mat_khau_bam_dang_ky="",
                        )
                    )
                ),
                name=ten_rang_buoc("kiem_tra", "phien_xac_thuc", "du_lieu_dang_ky_dung_loai"),
            ),
            models.CheckConstraint(
                condition=~Q(loai_xac_thuc="doi_email") | Q(tai_khoan__isnull=False),
                name=ten_rang_buoc("kiem_tra", "phien_xac_thuc", "doi_email_can_tai_khoan"),
            ),
            models.CheckConstraint(
                condition=Q(so_lan_nhap_sai__gte=0, so_lan_nhap_sai__lte=5),
                name=ten_rang_buoc("kiem_tra", "phien_xac_thuc", "so_lan_nhap_sai_toi_da"),
            ),
            models.CheckConstraint(
                condition=Q(so_lan_gui__gte=1, so_lan_gui__lte=5),
                name=ten_rang_buoc("kiem_tra", "phien_xac_thuc", "so_lan_gui_hop_le"),
            ),
            models.CheckConstraint(
                condition=Q(thoi_diem_het_han__gt=F("thoi_diem_gui_cuoi")),
                name=ten_rang_buoc("kiem_tra", "phien_xac_thuc", "het_han_sau_lan_gui"),
            ),
        ]

    def __str__(self):
        return f"{self.get_loai_xac_thuc_display()} · {self.email}"
