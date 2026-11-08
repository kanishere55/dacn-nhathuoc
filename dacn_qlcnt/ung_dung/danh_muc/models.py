import datetime

from django.contrib.gis.db.models import PointField
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now

from ung_dung.chung.anh import AnhCSDL, rang_buoc_anh
from ung_dung.chung.ten_csdl import (
    SO_DIEN_THOAI,
    rang_buoc_so,
    rang_buoc_van_ban,
    ten_rang_buoc,
)

MAU_SO_DIEN_THOAI_HOAC_RONG = f"^({SO_DIEN_THOAI[1:-1]})?$"


class ChiNhanh(models.Model):
    id_chi_nhanh = models.BigAutoField(
        db_column="id_chi_nhanh",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_chi_nhanh = models.TextField(
        db_column="ma_chi_nhanh", db_comment="Mã chi nhánh do quản trị nhập; văn bản một dòng."
    )
    ten_chi_nhanh = models.TextField(
        db_column="ten_chi_nhanh", db_comment="Tên hiển thị của cơ sở; văn bản một dòng."
    )
    dia_chi = models.TextField(
        db_column="dia_chi", db_comment="Địa chỉ cơ sở do quản trị nhập; văn bản một dòng."
    )
    vi_tri = PointField(
        geography=True,
        srid=4326,
        db_column="vi_tri",
        db_comment="Tọa độ kinh độ/vĩ độ WGS84 do quản trị nhập; điểm địa lý trên Trái Đất.",
    )
    dang_hoat_dong = models.BooleanField(
        db_column="dang_hoat_dong",
        db_comment="Chi nhánh đang tiếp nhận nghiệp vụ.",
        db_default=True,
    )
    so_dien_thoai = models.TextField(
        blank=True,
        db_default="",
        db_column="so_dien_thoai",
        db_comment="Số điện thoại của nhà thuốc, dạng nội địa; rỗng khi chưa có.",
    )
    gio_mo_cua = models.TimeField(
        default=datetime.time(7, 0),
        db_default=datetime.time(7, 0),
        db_column="gio_mo_cua",
        db_comment="Giờ mở cửa hằng ngày theo giờ Việt Nam.",
    )
    gio_dong_cua = models.TimeField(
        default=datetime.time(22, 0),
        db_default=datetime.time(22, 0),
        db_column="gio_dong_cua",
        db_comment="Giờ đóng cửa hằng ngày theo giờ Việt Nam, sau giờ mở cửa.",
    )

    class Meta:
        db_table = "chi_nhanh"
        db_table_comment = "Mỗi hàng là một chi nhánh trong chuỗi mô phỏng."
        verbose_name = "Mỗi hàng là một chi nhánh trong chuỗi mô phỏng."
        constraints = [
            *rang_buoc_van_ban("chi_nhanh", "ma_chi_nhanh", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("chi_nhanh", "ten_chi_nhanh", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("chi_nhanh", "dia_chi", rong=False, nhieu_dong=False),
            models.UniqueConstraint(
                fields=["ma_chi_nhanh"],
                name=ten_rang_buoc("duy_nhat", "chi_nhanh", *["ma_chi_nhanh"]),
            ),
            *rang_buoc_van_ban(
                "chi_nhanh", "so_dien_thoai", rong=True, dinh_dang=MAU_SO_DIEN_THOAI_HOAC_RONG
            ),
            models.CheckConstraint(
                condition=Q(gio_dong_cua__gt=F("gio_mo_cua")),
                name=ten_rang_buoc("kiem_tra", "chi_nhanh", "gio_dong_sau_gio_mo"),
            ),
        ]

    def __str__(self):
        return str(self.ten_chi_nhanh)


class DonViTinh(models.Model):
    id_don_vi_tinh = models.BigAutoField(
        db_column="id_don_vi_tinh",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_don_vi_tinh = models.TextField(
        db_column="ma_don_vi_tinh", db_comment="Mã đơn vị; văn bản một dòng."
    )
    ten_don_vi_tinh = models.TextField(
        db_column="ten_don_vi_tinh", db_comment="Tên đơn vị cơ sở; văn bản một dòng."
    )

    class Meta:
        db_table = "don_vi_tinh"
        db_table_comment = "Mỗi hàng là một đơn vị cơ sở có cùng nghĩa trong hệ thống."
        verbose_name = "Mỗi hàng là một đơn vị cơ sở có cùng nghĩa trong hệ thống."
        constraints = [
            *rang_buoc_van_ban("don_vi_tinh", "ma_don_vi_tinh", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("don_vi_tinh", "ten_don_vi_tinh", rong=False, nhieu_dong=False),
            models.UniqueConstraint(
                fields=["ma_don_vi_tinh"],
                name=ten_rang_buoc("duy_nhat", "don_vi_tinh", *["ma_don_vi_tinh"]),
            ),
        ]

    def __str__(self):
        return str(self.ten_don_vi_tinh)


class NhomATC(models.Model):
    id_nhom_atc = models.BigAutoField(
        db_column="id_nhom_atc",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_nhom_atc = models.TextField(
        db_column="ma_nhom_atc", db_comment="Mã ATC từ danh mục được dùng; văn bản một dòng."
    )
    ten_nhom_atc = models.TextField(
        db_column="ten_nhom_atc", db_comment="Diễn giải nhóm ATC; văn bản một dòng."
    )

    class Meta:
        db_table = "nhom_atc"
        db_table_comment = (
            "Mỗi hàng là một mã phân nhóm ATC, không biểu thị khả năng thay thế thuốc."
        )
        verbose_name = "Mỗi hàng là một mã phân nhóm ATC, không biểu thị khả năng thay thế thuốc."
        constraints = [
            *rang_buoc_van_ban("nhom_atc", "ma_nhom_atc", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("nhom_atc", "ten_nhom_atc", rong=False, nhieu_dong=False),
            models.UniqueConstraint(
                fields=["ma_nhom_atc"], name=ten_rang_buoc("duy_nhat", "nhom_atc", *["ma_nhom_atc"])
            ),
        ]

    def __str__(self):
        return str(self.ma_nhom_atc)


class NhaCungCap(models.Model):
    id_nha_cung_cap = models.BigAutoField(
        db_column="id_nha_cung_cap",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_nha_cung_cap = models.TextField(
        db_column="ma_nha_cung_cap", db_comment="Mã đối tác; văn bản một dòng."
    )
    ten_nha_cung_cap = models.TextField(
        db_column="ten_nha_cung_cap", db_comment="Tên đối tác; văn bản một dòng."
    )
    dia_chi = models.TextField(
        db_column="dia_chi",
        db_comment="Địa chỉ liên hệ; văn bản một dòng.",
        blank=True,
        db_default="",
    )
    so_dien_thoai = models.TextField(
        db_column="so_dien_thoai",
        db_comment="Số liên hệ do người dùng nhập; văn bản một dòng.",
        blank=True,
        db_default="",
    )
    dang_hoat_dong = models.BooleanField(
        db_column="dang_hoat_dong",
        db_comment="Đối tác đang được sử dụng khi nhập mới.",
        db_default=True,
    )

    class Meta:
        db_table = "nha_cung_cap"
        db_table_comment = "Mỗi hàng là một đối tác cung cấp thuốc."
        verbose_name = "Mỗi hàng là một đối tác cung cấp thuốc."
        constraints = [
            *rang_buoc_van_ban("nha_cung_cap", "ma_nha_cung_cap", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("nha_cung_cap", "ten_nha_cung_cap", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("nha_cung_cap", "dia_chi", rong=True, nhieu_dong=False),
            *rang_buoc_van_ban("nha_cung_cap", "so_dien_thoai", rong=True, nhieu_dong=False),
            models.UniqueConstraint(
                fields=["ma_nha_cung_cap"],
                name=ten_rang_buoc("duy_nhat", "nha_cung_cap", *["ma_nha_cung_cap"]),
            ),
        ]

    def __str__(self):
        return str(self.ten_nha_cung_cap)


class Thuoc(models.Model):
    id_thuoc = models.BigAutoField(
        db_column="id_thuoc",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_thuoc = models.TextField(
        db_column="ma_thuoc", db_comment="SKU sản phẩm theo quyết định Q01; văn bản một dòng."
    )
    ten_thuoc = models.TextField(
        db_column="ten_thuoc", db_comment="Tên thương mại của thuốc; văn bản một dòng."
    )
    nhom_atc = models.ForeignKey(
        "danh_muc.NhomATC",
        on_delete=models.PROTECT,
        db_column="id_nhom_atc",
        db_comment="Nhóm ATC của sản phẩm.",
    )
    don_vi_tinh = models.ForeignKey(
        "danh_muc.DonViTinh",
        on_delete=models.PROTECT,
        db_column="id_don_vi_tinh",
        db_comment="Đơn vị cơ sở để quản lý lượng của thuốc.",
    )
    ham_luong = models.TextField(
        db_column="ham_luong", db_comment="Hàm lượng do quản trị nhập; văn bản một dòng."
    )
    dang_bao_che = models.TextField(
        db_column="dang_bao_che", db_comment="Dạng bào chế; văn bản một dòng."
    )
    nha_san_xuat = models.TextField(
        db_column="nha_san_xuat", db_comment="Nhà sản xuất; văn bản một dòng."
    )
    gia_ban = models.DecimalField(
        db_column="gia_ban",
        db_comment="Giá hiện tại một đơn vị cơ sở do quản trị nhập; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.",
        max_digits=14,
        decimal_places=0,
    )
    nguong_canh_bao = models.IntegerField(
        db_column="nguong_canh_bao",
        db_comment="Ngưỡng lượng khả dụng thấp, theo đơn vị cơ sở; giới hạn số nguyên PostgreSQL 32 bit.",
        db_default=10,
    )
    dang_hoat_dong = models.BooleanField(
        db_column="dang_hoat_dong",
        db_comment="Thuốc còn được dùng cho nghiệp vụ mới.",
        db_default=True,
    )
    danh_muc_san_pham = models.ForeignKey(
        "danh_muc.DanhMucSanPham",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="id_danh_muc_san_pham",
        db_comment="Danh mục hiển thị cho khách; NULL khi chưa xếp danh mục.",
    )
    la_thuoc_ke_don = models.BooleanField(
        default=False,
        db_default=False,
        db_column="la_thuoc_ke_don",
        db_comment=(
            "Thuốc phải bán theo đơn; không bán giao hàng, chỉ đặt giữ và bán tại quầy "
            "khi dược sĩ đã kiểm tra đơn thuốc (Luật số 44/2024/QH15)."
        ),
    )
    hoat_chat = models.TextField(
        blank=True,
        db_default="",
        db_column="hoat_chat",
        db_comment="Hoạt chất và hàm lượng từng thành phần; văn bản một dòng, có thể rỗng.",
    )
    quy_cach_dong_goi = models.TextField(
        blank=True,
        db_default="",
        db_column="quy_cach_dong_goi",
        db_comment="Quy cách đóng gói, ví dụ hộp 10 vỉ x 10 viên; một dòng, có thể rỗng.",
    )
    nuoc_san_xuat = models.TextField(
        blank=True,
        db_default="",
        db_column="nuoc_san_xuat",
        db_comment="Nước sản xuất; văn bản một dòng, có thể rỗng.",
    )
    so_dang_ky = models.TextField(
        blank=True,
        db_default="",
        db_column="so_dang_ky",
        db_comment="Số đăng ký lưu hành do Bộ Y tế cấp; một dòng, có thể rỗng.",
    )
    mo_ta_ngan = models.TextField(
        blank=True,
        db_default="",
        db_column="mo_ta_ngan",
        db_comment="Mô tả ngắn hiện ở thẻ thuốc; văn bản một dòng, có thể rỗng.",
    )
    cong_dung = models.TextField(
        blank=True,
        db_default="",
        db_column="cong_dung",
        db_comment="Công dụng, chỉ định theo tờ hướng dẫn; văn bản nhiều dòng.",
    )
    cach_dung = models.TextField(
        blank=True,
        db_default="",
        db_column="cach_dung",
        db_comment="Liều dùng và cách dùng; văn bản nhiều dòng.",
    )
    chong_chi_dinh = models.TextField(
        blank=True,
        db_default="",
        db_column="chong_chi_dinh",
        db_comment="Chống chỉ định; văn bản nhiều dòng.",
    )
    tac_dung_phu = models.TextField(
        blank=True,
        db_default="",
        db_column="tac_dung_phu",
        db_comment="Tác dụng không mong muốn; văn bản nhiều dòng.",
    )
    luu_y = models.TextField(
        blank=True,
        db_default="",
        db_column="luu_y",
        db_comment="Thận trọng và lưu ý khi dùng; văn bản nhiều dòng.",
    )
    bao_quan = models.TextField(
        blank=True,
        db_default="",
        db_column="bao_quan",
        db_comment="Điều kiện bảo quản; văn bản một dòng, có thể rỗng.",
    )

    class Meta:
        db_table = "thuoc"
        db_table_comment = "Mỗi hàng là một sản phẩm thuốc dùng chung toàn chuỗi."
        verbose_name = "Mỗi hàng là một sản phẩm thuốc dùng chung toàn chuỗi."
        constraints = [
            *rang_buoc_van_ban("thuoc", "ma_thuoc", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("thuoc", "ten_thuoc", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("thuoc", "ham_luong", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("thuoc", "dang_bao_che", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("thuoc", "nha_san_xuat", rong=False, nhieu_dong=False),
            *rang_buoc_so("thuoc", "gia_ban", duong=False, tien=True),
            *rang_buoc_so("thuoc", "nguong_canh_bao", duong=False, tien=False),
            models.UniqueConstraint(
                fields=["ma_thuoc"], name=ten_rang_buoc("duy_nhat", "thuoc", *["ma_thuoc"])
            ),
            *[
                rang_buoc
                for cot in (
                    "hoat_chat",
                    "quy_cach_dong_goi",
                    "nuoc_san_xuat",
                    "so_dang_ky",
                    "mo_ta_ngan",
                    "bao_quan",
                )
                for rang_buoc in rang_buoc_van_ban("thuoc", cot, rong=True)
            ],
            *[
                rang_buoc
                for cot in ("cong_dung", "cach_dung", "chong_chi_dinh", "tac_dung_phu", "luu_y")
                for rang_buoc in rang_buoc_van_ban("thuoc", cot, rong=True, nhieu_dong=True)
            ],
        ]

    def __str__(self):
        return str(self.ten_thuoc)


class QuyDoiBaoGoi(models.Model):
    id_quy_doi_bao_goi = models.BigAutoField(
        db_column="id_quy_doi_bao_goi",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    thuoc = models.ForeignKey(
        "danh_muc.Thuoc",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_thuoc",
        db_comment="Sản phẩm sở hữu quy đổi.",
    )
    ten_quy_doi_bao_goi = models.TextField(
        db_column="ten_quy_doi_bao_goi", db_comment="Tên bao gói, ví dụ hộp; văn bản một dòng."
    )
    he_so = models.IntegerField(
        db_column="he_so",
        db_comment="Số đơn vị cơ sở trong một bao gói; giới hạn số nguyên PostgreSQL 32 bit.",
    )

    class Meta:
        db_table = "quy_doi_bao_goi"
        db_table_comment = "Mỗi hàng là một bao gói quy đổi của riêng một thuốc."
        verbose_name = "Mỗi hàng là một bao gói quy đổi của riêng một thuốc."
        constraints = [
            *rang_buoc_van_ban(
                "quy_doi_bao_goi", "ten_quy_doi_bao_goi", rong=False, nhieu_dong=False
            ),
            *rang_buoc_so("quy_doi_bao_goi", "he_so", duong=True, tien=False),
            models.UniqueConstraint(
                fields=["thuoc", "ten_quy_doi_bao_goi"],
                name=ten_rang_buoc(
                    "duy_nhat", "quy_doi_bao_goi", *["id_thuoc", "ten_quy_doi_bao_goi"]
                ),
            ),
        ]

    def __str__(self):
        return str(self.ten_quy_doi_bao_goi)


class NhanVien(models.Model):
    id_nhan_vien = models.BigAutoField(
        db_column="id_nhan_vien",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_nhan_vien = models.TextField(
        db_column="ma_nhan_vien", db_comment="Mã nhân viên; văn bản một dòng."
    )
    ten_nhan_vien = models.TextField(
        db_column="ten_nhan_vien", db_comment="Họ tên nhân viên; văn bản một dòng."
    )
    tai_khoan = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_tai_khoan",
        db_comment="Tài khoản làm việc của nhân viên.",
    )
    so_dien_thoai = models.TextField(
        db_column="so_dien_thoai",
        db_comment="Số liên hệ; văn bản một dòng.",
        blank=True,
        db_default="",
    )

    class Meta:
        db_table = "nhan_vien"
        db_table_comment = "Mỗi hàng là hồ sơ nhân viên, phạm vi làm việc lấy từ tài khoản."
        verbose_name = "Mỗi hàng là hồ sơ nhân viên, phạm vi làm việc lấy từ tài khoản."
        constraints = [
            *rang_buoc_van_ban("nhan_vien", "ma_nhan_vien", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("nhan_vien", "ten_nhan_vien", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("nhan_vien", "so_dien_thoai", rong=True, nhieu_dong=False),
            models.UniqueConstraint(
                fields=["ma_nhan_vien"],
                name=ten_rang_buoc("duy_nhat", "nhan_vien", *["ma_nhan_vien"]),
            ),
            models.UniqueConstraint(
                fields=["tai_khoan"], name=ten_rang_buoc("duy_nhat", "nhan_vien", *["id_tai_khoan"])
            ),
        ]

    def __str__(self):
        return str(self.ten_nhan_vien)


class DanhMucSanPham(models.Model):
    id_danh_muc_san_pham = models.BigAutoField(
        primary_key=True,
        db_column="id_danh_muc_san_pham",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
    )
    ma_danh_muc_san_pham = models.TextField(
        db_column="ma_danh_muc_san_pham",
        db_comment="Mã danh mục do quản trị nhập, dùng trên đường dẫn lọc.",
    )
    ten_danh_muc_san_pham = models.TextField(
        db_column="ten_danh_muc_san_pham",
        db_comment="Tên danh mục hiển thị cho khách, ví dụ giảm đau hạ sốt; một dòng.",
    )
    mo_ta = models.TextField(
        blank=True,
        db_default="",
        db_column="mo_ta",
        db_comment="Mô tả ngắn của danh mục; văn bản một dòng, có thể rỗng.",
    )
    bieu_tuong = models.TextField(
        default="pill",
        db_default="pill",
        db_column="bieu_tuong",
        db_comment="Tên biểu tượng Lucide hiển thị cạnh danh mục, chữ thường và gạch ngang.",
    )
    thu_tu = models.SmallIntegerField(
        default=0,
        db_default=0,
        db_column="thu_tu",
        db_comment="Thứ tự hiển thị, số nhỏ đứng trước.",
    )
    dang_hien_thi = models.BooleanField(
        default=True,
        db_default=True,
        db_column="dang_hien_thi",
        db_comment="Danh mục đang hiện trên website khách.",
    )

    class Meta:
        db_table = "danh_muc_san_pham"
        db_table_comment = "Mỗi hàng là một nhóm sản phẩm khách dùng để duyệt website."
        verbose_name = "danh mục sản phẩm"
        ordering = ["thu_tu", "ten_danh_muc_san_pham"]
        constraints = [
            *rang_buoc_van_ban("danh_muc_san_pham", "ma_danh_muc_san_pham"),
            *rang_buoc_van_ban("danh_muc_san_pham", "ten_danh_muc_san_pham"),
            *rang_buoc_van_ban("danh_muc_san_pham", "mo_ta", rong=True),
            *rang_buoc_van_ban(
                "danh_muc_san_pham", "bieu_tuong", dinh_dang=r"^[a-z0-9]+(-[a-z0-9]+)*$"
            ),
            models.UniqueConstraint(
                fields=["ma_danh_muc_san_pham"],
                name=ten_rang_buoc("duy_nhat", "danh_muc_san_pham", "ma_danh_muc_san_pham"),
            ),
            models.CheckConstraint(
                condition=Q(thu_tu__gte=0),
                name=ten_rang_buoc("kiem_tra", "danh_muc_san_pham", "thu_tu_khong_am"),
            ),
        ]

    def __str__(self):
        return str(self.ten_danh_muc_san_pham)


class AnhThuoc(AnhCSDL):
    id_anh_thuoc = models.BigAutoField(
        primary_key=True,
        db_column="id_anh_thuoc",
        db_comment="Định danh nội bộ PostgreSQL cấp, dùng trên đường dẫn ảnh.",
    )
    thuoc = models.ForeignKey(
        "danh_muc.Thuoc",
        on_delete=models.PROTECT,
        related_name="cac_anh",
        db_index=False,
        db_column="id_thuoc",
        db_comment="Thuốc sở hữu ảnh.",
    )

    class Meta:
        db_table = "anh_thuoc"
        db_table_comment = "Mỗi hàng là một ảnh sản phẩm của thuốc, lưu bytea."
        verbose_name = "ảnh thuốc"
        ordering = ["thu_tu", "id_anh_thuoc"]
        indexes = [
            models.Index(
                fields=["thuoc", "thu_tu"],
                name=ten_rang_buoc("chi_muc", "anh_thuoc", "id_thuoc", "thu_tu"),
            )
        ]
        constraints = rang_buoc_anh("anh_thuoc")


class AnhChiNhanh(AnhCSDL):
    id_anh_chi_nhanh = models.BigAutoField(
        primary_key=True,
        db_column="id_anh_chi_nhanh",
        db_comment="Định danh nội bộ PostgreSQL cấp, dùng trên đường dẫn ảnh.",
    )
    chi_nhanh = models.ForeignKey(
        "danh_muc.ChiNhanh",
        on_delete=models.PROTECT,
        related_name="cac_anh",
        db_index=False,
        db_column="id_chi_nhanh",
        db_comment="Chi nhánh sở hữu ảnh.",
    )

    class Meta:
        db_table = "anh_chi_nhanh"
        db_table_comment = "Mỗi hàng là một ảnh mặt tiền hoặc bên trong nhà thuốc, lưu bytea."
        verbose_name = "ảnh chi nhánh"
        ordering = ["thu_tu", "id_anh_chi_nhanh"]
        indexes = [
            models.Index(
                fields=["chi_nhanh", "thu_tu"],
                name=ten_rang_buoc("chi_muc", "anh_chi_nhanh", "id_chi_nhanh", "thu_tu"),
            )
        ]
        constraints = rang_buoc_anh("anh_chi_nhanh")


class KhuyenMai(models.Model):
    id_khuyen_mai = models.BigAutoField(
        primary_key=True,
        db_column="id_khuyen_mai",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
    )
    ma_khuyen_mai = models.TextField(
        db_column="ma_khuyen_mai", db_comment="Mã chương trình do quản trị nhập."
    )
    ten_khuyen_mai = models.TextField(
        db_column="ten_khuyen_mai", db_comment="Tên chương trình hiển thị cho khách; một dòng."
    )
    thuoc = models.ForeignKey(
        "danh_muc.Thuoc",
        on_delete=models.PROTECT,
        related_name="cac_khuyen_mai",
        db_index=False,
        db_column="id_thuoc",
        db_comment="Thuốc được giảm giá.",
    )
    phan_tram_giam = models.SmallIntegerField(
        db_column="phan_tram_giam",
        db_comment="Phần trăm giảm trên giá bán, từ 1 đến 90.",
    )
    ngay_bat_dau = models.DateField(
        db_column="ngay_bat_dau", db_comment="Ngày đầu áp dụng, tính theo giờ Việt Nam."
    )
    ngay_ket_thuc = models.DateField(
        db_column="ngay_ket_thuc", db_comment="Ngày cuối áp dụng, tính cả ngày này."
    )
    dang_hoat_dong = models.BooleanField(
        default=True,
        db_default=True,
        db_column="dang_hoat_dong",
        db_comment="Quản trị có thể dừng chương trình trước hạn; không xóa để giữ lịch sử.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_default=Now(), db_column="thoi_diem_tao", db_comment="Thời điểm tạo chương trình."
    )

    class Meta:
        db_table = "khuyen_mai"
        db_table_comment = (
            "Mỗi hàng là một đợt giảm giá theo phần trăm cho một thuốc; service không "
            "cho hai đợt đang hoạt động của cùng thuốc trùng ngày."
        )
        verbose_name = "khuyến mãi"
        ordering = ["-ngay_bat_dau", "-id_khuyen_mai"]
        indexes = [
            models.Index(
                fields=["thuoc", "ngay_bat_dau"],
                name=ten_rang_buoc("chi_muc", "khuyen_mai", "id_thuoc", "ngay_bat_dau"),
            )
        ]
        constraints = [
            *rang_buoc_van_ban("khuyen_mai", "ma_khuyen_mai"),
            *rang_buoc_van_ban("khuyen_mai", "ten_khuyen_mai"),
            models.UniqueConstraint(
                fields=["ma_khuyen_mai"],
                name=ten_rang_buoc("duy_nhat", "khuyen_mai", "ma_khuyen_mai"),
            ),
            models.CheckConstraint(
                condition=Q(phan_tram_giam__gte=1, phan_tram_giam__lte=90),
                name=ten_rang_buoc("kiem_tra", "khuyen_mai", "phan_tram_giam_hop_le"),
            ),
            models.CheckConstraint(
                condition=Q(ngay_ket_thuc__gte=F("ngay_bat_dau")),
                name=ten_rang_buoc("kiem_tra", "khuyen_mai", "ket_thuc_sau_bat_dau"),
            ),
        ]

    def __str__(self):
        return f"{self.ten_khuyen_mai} (-{self.phan_tram_giam}%)"
