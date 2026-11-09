"""Nội dung website do quản trị chuỗi soạn: banner trang chủ, thông tin cửa hàng, trang tĩnh."""

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now

from ung_dung.chung.anh import AnhCSDL, rang_buoc_anh
from ung_dung.chung.ten_csdl import EMAIL, rang_buoc_van_ban, ten_rang_buoc

MAU_HEX = r"^#[0-9a-f]{6}$"
DUONG_DAN_NOI_BO = r"^/[A-Za-z0-9/_.?=&%-]*$"
DUONG_DAN_TRANG = r"^[a-z0-9]+(-[a-z0-9]+)*$"
HOTLINE = r"^[0-9]{4,11}$"


class BannerTrangChu(AnhCSDL):
    id_banner_trang_chu = models.BigAutoField(
        primary_key=True,
        db_column="id_banner_trang_chu",
        db_comment="Định danh nội bộ PostgreSQL cấp, dùng trên đường dẫn ảnh banner.",
    )
    tieu_de = models.TextField(db_column="tieu_de", db_comment="Tiêu đề lớn của banner; một dòng.")
    mo_ta = models.TextField(
        default="",
        db_default="",
        blank=True,
        db_column="mo_ta",
        db_comment="Câu mô tả ngắn dưới tiêu đề; một dòng, rỗng khi không cần.",
    )
    nhan_nut = models.TextField(
        db_column="nhan_nut", db_comment="Chữ trên nút hành động của banner; một dòng."
    )
    duong_dan = models.TextField(
        db_column="duong_dan",
        db_comment="Đường dẫn nội bộ bắt đầu bằng / mà nút banner mở; không nhận liên kết ngoài.",
    )
    mau_nen = models.TextField(
        default="#e7f4ee",
        db_default="#e7f4ee",
        db_column="mau_nen",
        db_comment="Màu nền khối hero khi banner hiện, dạng #rrggbb chữ thường.",
    )
    nguon_anh = models.TextField(
        default="",
        db_default="",
        blank=True,
        db_column="nguon_anh",
        db_comment="Nguồn và giấy phép của ảnh (ví dụ StockSnap, CC0); rỗng khi ảnh tự tạo.",
    )
    dang_hien_thi = models.BooleanField(
        default=True,
        db_default=True,
        db_column="dang_hien_thi",
        db_comment="Quản trị tắt để ẩn banner mà không xóa.",
    )
    ngay_bat_dau = models.DateField(
        null=True,
        blank=True,
        db_column="ngay_bat_dau",
        db_comment="Ngày bắt đầu hiện; NULL là hiện ngay.",
    )
    ngay_ket_thuc = models.DateField(
        null=True,
        blank=True,
        db_column="ngay_ket_thuc",
        db_comment="Ngày cuối cùng hiện; NULL là không hẹn ngày kết thúc.",
    )

    class Meta:
        db_table = "banner_trang_chu"
        db_table_comment = "Mỗi hàng là một banner trong băng chuyền đầu trang chủ, ảnh lưu bytea."
        verbose_name = "banner trang chủ"
        ordering = ["thu_tu", "id_banner_trang_chu"]
        constraints = [
            *rang_buoc_anh("banner_trang_chu"),
            *rang_buoc_van_ban("banner_trang_chu", "tieu_de"),
            *rang_buoc_van_ban("banner_trang_chu", "mo_ta", rong=True),
            *rang_buoc_van_ban("banner_trang_chu", "nhan_nut"),
            *rang_buoc_van_ban("banner_trang_chu", "duong_dan", dinh_dang=DUONG_DAN_NOI_BO),
            *rang_buoc_van_ban("banner_trang_chu", "mau_nen", dinh_dang=MAU_HEX),
            *rang_buoc_van_ban("banner_trang_chu", "nguon_anh", rong=True),
            models.CheckConstraint(
                condition=Q(ngay_bat_dau__isnull=True)
                | Q(ngay_ket_thuc__isnull=True)
                | Q(ngay_ket_thuc__gte=F("ngay_bat_dau")),
                name=ten_rang_buoc("kiem_tra", "banner_trang_chu", "ket_thuc_sau_bat_dau"),
            ),
        ]

    def __str__(self):
        return self.tieu_de


class ThongTinCuaHang(models.Model):
    id_thong_tin_cua_hang = models.SmallIntegerField(
        primary_key=True,
        default=1,
        db_column="id_thong_tin_cua_hang",
        db_comment="Luôn bằng 1: bảng chỉ có một hàng cấu hình.",
    )
    ten_thuong_hieu = models.TextField(
        db_column="ten_thuong_hieu",
        db_comment="Tên chuỗi nhà thuốc trên đầu trang, email, hóa đơn.",
    )
    khau_hieu = models.TextField(
        default="",
        db_default="",
        blank=True,
        db_column="khau_hieu",
        db_comment="Dòng giới thiệu ngắn dưới tên thương hiệu; rỗng khi không dùng.",
    )
    hotline = models.TextField(
        db_column="hotline", db_comment="Số điện thoại tư vấn chung, chỉ gồm 4 đến 11 chữ số."
    )
    email_lien_he = models.TextField(
        db_column="email_lien_he", db_comment="Email nhận liên hệ của khách; chữ thường."
    )
    dia_chi_tru_so = models.TextField(
        db_column="dia_chi_tru_so", db_comment="Địa chỉ trụ sở in ở chân trang; một dòng."
    )
    gio_lam_viec = models.TextField(
        db_column="gio_lam_viec", db_comment="Giờ phục vụ chung hiển thị cho khách; một dòng."
    )
    giay_phep_kinh_doanh = models.TextField(
        default="",
        db_default="",
        blank=True,
        db_column="giay_phep_kinh_doanh",
        db_comment="Số giấy chứng nhận đủ điều kiện kinh doanh dược; rỗng khi chưa nhập.",
    )
    thoi_diem_cap_nhat = models.DateTimeField(
        db_default=Now(), db_column="thoi_diem_cap_nhat", db_comment="Lần lưu gần nhất."
    )

    class Meta:
        db_table = "thong_tin_cua_hang"
        db_table_comment = "Một hàng duy nhất chứa thông tin liên hệ chung của chuỗi nhà thuốc."
        verbose_name = "thông tin cửa hàng"
        constraints = [
            models.CheckConstraint(
                condition=Q(id_thong_tin_cua_hang=1),
                name=ten_rang_buoc("kiem_tra", "thong_tin_cua_hang", "chi_mot_hang"),
            ),
            *rang_buoc_van_ban("thong_tin_cua_hang", "ten_thuong_hieu"),
            *rang_buoc_van_ban("thong_tin_cua_hang", "khau_hieu", rong=True),
            *rang_buoc_van_ban("thong_tin_cua_hang", "hotline", dinh_dang=HOTLINE),
            *rang_buoc_van_ban("thong_tin_cua_hang", "email_lien_he", dinh_dang=EMAIL),
            *rang_buoc_van_ban("thong_tin_cua_hang", "dia_chi_tru_so"),
            *rang_buoc_van_ban("thong_tin_cua_hang", "gio_lam_viec"),
            *rang_buoc_van_ban("thong_tin_cua_hang", "giay_phep_kinh_doanh", rong=True),
        ]

    def __str__(self):
        return self.ten_thuong_hieu


class TrangNoiDung(models.Model):
    id_trang_noi_dung = models.BigAutoField(
        primary_key=True,
        db_column="id_trang_noi_dung",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
    )
    duong_dan_trang = models.TextField(
        db_column="duong_dan_trang",
        db_comment="Phần cuối đường dẫn /trang/<...>/, chữ thường không dấu nối bằng gạch ngang.",
    )
    tieu_de = models.TextField(db_column="tieu_de", db_comment="Tiêu đề trang; một dòng.")
    tom_tat = models.TextField(
        default="",
        db_default="",
        blank=True,
        db_column="tom_tat",
        db_comment="Câu tóm tắt dưới tiêu đề và trong thẻ mô tả trang; một dòng.",
    )
    noi_dung_trang = models.TextField(
        db_column="noi_dung_trang",
        db_comment="Nội dung trang; HTML định dạng đã làm sạch bằng nh3.",
    )
    dang_hien_thi = models.BooleanField(
        default=True,
        db_default=True,
        db_column="dang_hien_thi",
        db_comment="Tắt để ẩn trang khỏi website và chân trang.",
    )
    thu_tu = models.SmallIntegerField(
        default=0,
        db_default=0,
        db_column="thu_tu",
        db_comment="Thứ tự liên kết ở chân trang, số nhỏ đứng trước.",
    )
    thoi_diem_cap_nhat = models.DateTimeField(
        db_default=Now(), db_column="thoi_diem_cap_nhat", db_comment="Lần lưu gần nhất."
    )

    class Meta:
        db_table = "trang_noi_dung"
        db_table_comment = "Mỗi hàng là một trang thông tin: giới thiệu, chính sách, hướng dẫn."
        verbose_name = "trang nội dung"
        ordering = ["thu_tu", "id_trang_noi_dung"]
        constraints = [
            *rang_buoc_van_ban("trang_noi_dung", "duong_dan_trang", dinh_dang=DUONG_DAN_TRANG),
            models.UniqueConstraint(
                fields=["duong_dan_trang"],
                name=ten_rang_buoc("duy_nhat", "trang_noi_dung", "duong_dan_trang"),
            ),
            *rang_buoc_van_ban("trang_noi_dung", "tieu_de"),
            *rang_buoc_van_ban("trang_noi_dung", "tom_tat", rong=True),
            *rang_buoc_van_ban("trang_noi_dung", "noi_dung_trang", nhieu_dong=True),
            models.CheckConstraint(
                condition=Q(thu_tu__gte=0),
                name=ten_rang_buoc("kiem_tra", "trang_noi_dung", "thu_tu_khong_am"),
            ),
        ]

    def __str__(self):
        return self.tieu_de
