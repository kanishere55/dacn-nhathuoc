from django.contrib.gis.db.models import PointField
from django.db import models

from ung_dung.chung.ten_csdl import rang_buoc_so, rang_buoc_van_ban, ten_rang_buoc


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
