from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now

from ung_dung.chung.ten_csdl import rang_buoc_so, rang_buoc_van_ban, ten_rang_buoc


class DonDatGiu(models.Model):
    id_don_dat_giu = models.BigAutoField(
        db_column="id_don_dat_giu",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_don_dat_giu = models.TextField(
        db_column="ma_don_dat_giu", db_comment="Mã đơn hệ thống cấp; văn bản một dòng."
    )
    khach_hang = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        on_delete=models.PROTECT,
        db_column="id_tai_khoan_khach",
        db_comment="Khách sở hữu đơn.",
    )
    chi_nhanh = models.ForeignKey(
        "danh_muc.ChiNhanh",
        on_delete=models.PROTECT,
        db_column="id_chi_nhanh",
        db_comment="Chi nhánh duy nhất nhận đơn.",
    )
    trang_thai = models.TextField(
        db_column="trang_thai",
        db_comment="dang_giu: giữ đang hiệu lực; da_huy: khách/nhân viên hủy; het_han: hết thời hạn; da_nhan: nhận tại quầy.",
        db_default="dang_giu",
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )
    thoi_diem_het_giu = models.DateTimeField(
        db_column="thoi_diem_het_giu",
        db_comment="Mốc kết thúc giữ, hệ thống đặt 24 giờ sau xác nhận.",
    )

    class Meta:
        db_table = "don_dat_giu"
        db_table_comment = "Mỗi hàng là một đơn giữ toàn bộ nhu cầu ở một chi nhánh."
        verbose_name = "Mỗi hàng là một đơn giữ toàn bộ nhu cầu ở một chi nhánh."
        constraints = [
            *rang_buoc_van_ban("don_dat_giu", "ma_don_dat_giu", rong=False, nhieu_dong=False),
            models.UniqueConstraint(
                fields=["ma_don_dat_giu"],
                name=ten_rang_buoc("duy_nhat", "don_dat_giu", *["ma_don_dat_giu"]),
            ),
            models.CheckConstraint(
                condition=Q(trang_thai__in=["dang_giu", "da_huy", "het_han", "da_nhan"]),
                name="kiem_tra__don_dat_giu__trang_thai_hop_le",
            ),
            models.CheckConstraint(
                condition=Q(thoi_diem_het_giu__gt=F("thoi_diem_tao")),
                name="kiem_tra__don_dat_giu__het_giu_sau_khi_tao",
            ),
        ]

    def __str__(self):
        return str(self.ma_don_dat_giu)


class ChiTietDonDatGiu(models.Model):
    id_chi_tiet_don_dat_giu = models.BigAutoField(
        db_column="id_chi_tiet_don_dat_giu",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    don_dat_giu = models.ForeignKey(
        "ban_hang.DonDatGiu",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_don_dat_giu",
        db_comment="Đơn giữ sở hữu dòng.",
    )
    thuoc = models.ForeignKey(
        "danh_muc.Thuoc",
        on_delete=models.PROTECT,
        db_column="id_thuoc",
        db_comment="Thuốc đúng sản phẩm khách yêu cầu.",
    )
    so_luong = models.IntegerField(
        db_column="so_luong",
        db_comment="Lượng cơ sở được yêu cầu; giới hạn số nguyên PostgreSQL 32 bit.",
    )

    class Meta:
        db_table = "chi_tiet_don_dat_giu"
        db_table_comment = "Mỗi hàng là nhu cầu một thuốc trong đơn giữ."
        verbose_name = "Mỗi hàng là nhu cầu một thuốc trong đơn giữ."
        constraints = [
            *rang_buoc_so("chi_tiet_don_dat_giu", "so_luong", duong=True, tien=False),
            models.UniqueConstraint(
                fields=["don_dat_giu", "thuoc"],
                name=ten_rang_buoc(
                    "duy_nhat", "chi_tiet_don_dat_giu", *["id_don_dat_giu", "id_thuoc"]
                ),
            ),
        ]


class PhanBoDatGiu(models.Model):
    id_phan_bo_dat_giu = models.BigAutoField(
        db_column="id_phan_bo_dat_giu",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    chi_tiet_don_dat_giu = models.ForeignKey(
        "ban_hang.ChiTietDonDatGiu",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_chi_tiet_don_dat_giu",
        db_comment="Dòng nhu cầu giữ.",
    )
    ton_kho = models.ForeignKey(
        "kho.TonKho",
        on_delete=models.PROTECT,
        db_column="id_ton_kho",
        db_comment="Hàng tồn của lô tại chi nhánh đơn.",
    )
    so_luong = models.IntegerField(
        db_column="so_luong",
        db_comment="Lượng cơ sở đang phân bổ; giới hạn số nguyên PostgreSQL 32 bit.",
    )

    class Meta:
        db_table = "phan_bo_dat_giu"
        db_table_comment = "Mỗi hàng là lượng một dòng giữ được phân bổ vào hàng tồn của một lô."
        verbose_name = "Mỗi hàng là lượng một dòng giữ được phân bổ vào hàng tồn của một lô."
        constraints = [
            *rang_buoc_so("phan_bo_dat_giu", "so_luong", duong=True, tien=False),
            models.UniqueConstraint(
                fields=["chi_tiet_don_dat_giu", "ton_kho"],
                name=ten_rang_buoc(
                    "duy_nhat", "phan_bo_dat_giu", *["id_chi_tiet_don_dat_giu", "id_ton_kho"]
                ),
            ),
        ]


class PhieuBan(models.Model):
    id_phieu_ban = models.BigAutoField(
        db_column="id_phieu_ban",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_phieu_ban = models.TextField(
        db_column="ma_phieu_ban", db_comment="Mã phiếu hệ thống cấp; văn bản một dòng."
    )
    khoa_yeu_cau = models.TextField(
        db_column="khoa_yeu_cau",
        db_comment="UUID chống xác nhận hai lần từ cùng form; văn bản một dòng.",
    )
    chi_nhanh = models.ForeignKey(
        "danh_muc.ChiNhanh",
        on_delete=models.PROTECT,
        db_column="id_chi_nhanh",
        db_comment="Chi nhánh bán.",
    )
    nguoi_lap = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        on_delete=models.PROTECT,
        db_column="id_tai_khoan_lap",
        db_comment="Nhân viên xác nhận bán.",
    )
    don_dat_giu = models.ForeignKey(
        "ban_hang.DonDatGiu",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_don_dat_giu",
        db_comment="Đơn giữ đã nhận; NULL nghĩa là bán trực tiếp.",
        null=True,
        blank=True,
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "phieu_ban"
        db_table_comment = "Mỗi hàng là một lần bán và nhận thanh toán trực tiếp tại quầy."
        verbose_name = "Mỗi hàng là một lần bán và nhận thanh toán trực tiếp tại quầy."
        constraints = [
            *rang_buoc_van_ban("phieu_ban", "ma_phieu_ban", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("phieu_ban", "khoa_yeu_cau", rong=False, nhieu_dong=False),
            models.UniqueConstraint(
                fields=["ma_phieu_ban"],
                name=ten_rang_buoc("duy_nhat", "phieu_ban", *["ma_phieu_ban"]),
            ),
            models.UniqueConstraint(
                fields=["khoa_yeu_cau"],
                name=ten_rang_buoc("duy_nhat", "phieu_ban", *["khoa_yeu_cau"]),
            ),
            models.UniqueConstraint(
                fields=["don_dat_giu"],
                name=ten_rang_buoc("duy_nhat", "phieu_ban", *["id_don_dat_giu"]),
            ),
        ]

    def __str__(self):
        return str(self.ma_phieu_ban)


class ChiTietPhieuBan(models.Model):
    id_chi_tiet_phieu_ban = models.BigAutoField(
        db_column="id_chi_tiet_phieu_ban",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    phieu_ban = models.ForeignKey(
        "ban_hang.PhieuBan",
        on_delete=models.PROTECT,
        db_column="id_phieu_ban",
        db_comment="Phiếu bán.",
    )
    thuoc = models.ForeignKey(
        "danh_muc.Thuoc",
        on_delete=models.PROTECT,
        db_column="id_thuoc",
        db_comment="Sản phẩm được bán.",
    )
    ma_thuoc_luc_ban = models.TextField(
        db_column="ma_thuoc_luc_ban", db_comment="Mã sản phẩm được chụp khi bán; văn bản một dòng."
    )
    ten_thuoc_luc_ban = models.TextField(
        db_column="ten_thuoc_luc_ban",
        db_comment="Tên sản phẩm được chụp khi bán; văn bản một dòng.",
    )
    so_luong = models.IntegerField(
        db_column="so_luong", db_comment="Lượng cơ sở bán; giới hạn số nguyên PostgreSQL 32 bit."
    )
    don_gia = models.DecimalField(
        db_column="don_gia",
        db_comment="Giá một đơn vị cơ sở khi xác nhận; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.",
        max_digits=14,
        decimal_places=0,
    )

    class Meta:
        db_table = "chi_tiet_phieu_ban"
        db_table_comment = "Mỗi hàng là một thuốc đã bán với giá và tên chụp tại quầy."
        verbose_name = "Mỗi hàng là một thuốc đã bán với giá và tên chụp tại quầy."
        constraints = [
            *rang_buoc_van_ban(
                "chi_tiet_phieu_ban", "ma_thuoc_luc_ban", rong=False, nhieu_dong=False
            ),
            *rang_buoc_van_ban(
                "chi_tiet_phieu_ban", "ten_thuoc_luc_ban", rong=False, nhieu_dong=False
            ),
            *rang_buoc_so("chi_tiet_phieu_ban", "so_luong", duong=True, tien=False),
            *rang_buoc_so("chi_tiet_phieu_ban", "don_gia", duong=False, tien=True),
        ]


class PhanBoPhieuBan(models.Model):
    id_phan_bo_phieu_ban = models.BigAutoField(
        db_column="id_phan_bo_phieu_ban",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    chi_tiet_phieu_ban = models.ForeignKey(
        "ban_hang.ChiTietPhieuBan",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_chi_tiet_phieu_ban",
        db_comment="Dòng thuốc bán.",
    )
    ton_kho = models.ForeignKey(
        "kho.TonKho",
        on_delete=models.PROTECT,
        db_column="id_ton_kho",
        db_comment="Hàng tồn thực xuất.",
    )
    so_luong = models.IntegerField(
        db_column="so_luong", db_comment="Lượng cơ sở xuất; giới hạn số nguyên PostgreSQL 32 bit."
    )

    class Meta:
        db_table = "phan_bo_phieu_ban"
        db_table_comment = "Mỗi hàng là lượng thực xuất của một dòng bán từ một lô."
        verbose_name = "Mỗi hàng là lượng thực xuất của một dòng bán từ một lô."
        constraints = [
            *rang_buoc_so("phan_bo_phieu_ban", "so_luong", duong=True, tien=False),
            models.UniqueConstraint(
                fields=["chi_tiet_phieu_ban", "ton_kho"],
                name=ten_rang_buoc(
                    "duy_nhat", "phan_bo_phieu_ban", *["id_chi_tiet_phieu_ban", "id_ton_kho"]
                ),
            ),
        ]
