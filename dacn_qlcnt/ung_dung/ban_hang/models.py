from django.contrib.gis.db.models import PointField
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now

from ung_dung.chung.ten_csdl import (
    SO_DIEN_THOAI,
    rang_buoc_so,
    rang_buoc_van_ban,
    ten_rang_buoc,
)

TRANG_THAI_DON = [
    ("cho_thanh_toan", "Chờ thanh toán"),
    ("cho_xac_nhan", "Chờ xác nhận"),
    ("dang_giu", "Đang giữ tại quầy"),
    ("dang_chuan_bi", "Đang chuẩn bị"),
    ("dang_giao", "Đang giao"),
    ("hoan_thanh", "Hoàn thành"),
    ("da_huy", "Đã hủy"),
    ("het_han", "Hết hạn giữ"),
    ("giao_that_bai", "Giao thất bại"),
]
# Lượng giữ chỉ có hiệu lực ở các trạng thái này và trước thoi_diem_het_giu.
TRANG_THAI_GIU = ("cho_thanh_toan", "cho_xac_nhan", "dang_giu")
TRANG_THAI_NHAN_TAI_QUAY = ("dang_giu", "hoan_thanh", "da_huy", "het_han")
TRANG_THAI_GIAO_HANG = (
    "cho_thanh_toan",
    "cho_xac_nhan",
    "dang_chuan_bi",
    "dang_giao",
    "hoan_thanh",
    "da_huy",
    "giao_that_bai",
)
HINH_THUC_NHAN = [("nhan_tai_quay", "Nhận tại nhà thuốc"), ("giao_hang", "Giao tận nơi")]
PHUONG_THUC_THANH_TOAN = [
    ("tai_quay", "Thanh toán tại quầy"),
    ("cod", "Thanh toán khi nhận hàng (COD)"),
    ("chuyen_khoan", "Chuyển khoản qua mã VietQR"),
    ("momo", "Ví MoMo"),
]
TRANG_THAI_THANH_TOAN = [
    ("chua_thanh_toan", "Chưa thanh toán"),
    ("da_thanh_toan", "Đã thanh toán"),
    ("cho_hoan_tien", "Chờ hoàn tiền"),
    ("da_hoan_tien", "Đã hoàn tiền"),
]


def _ma(cac_lua_chon):
    return [ma for ma, _ in cac_lua_chon]


def _tien(ten, mo_ta, **them):
    return models.DecimalField(
        max_digits=14,
        decimal_places=0,
        db_column=ten,
        db_comment=f"{mo_ta}; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.",
        **them,
    )


class DonHang(models.Model):
    id_don_hang = models.BigAutoField(
        db_column="id_don_hang",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_don_hang = models.TextField(
        db_column="ma_don_hang", db_comment="Mã đơn hệ thống cấp; văn bản một dòng."
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
        db_comment="Chi nhánh duy nhất giữ hàng và xử lý đơn.",
    )
    hinh_thuc_nhan = models.TextField(
        choices=HINH_THUC_NHAN,
        default="nhan_tai_quay",
        db_default="nhan_tai_quay",
        db_column="hinh_thuc_nhan",
        db_comment="nhan_tai_quay: đặt giữ, nhận và trả tiền tại quầy; giao_hang: giao tới địa chỉ.",
    )
    trang_thai = models.TextField(
        choices=TRANG_THAI_DON,
        default="dang_giu",
        db_default="dang_giu",
        db_column="trang_thai",
        db_comment=(
            "Trạng thái xử lý; chỉ service đổi theo bảng chuyển hợp lệ và ghi lich_su_don_hang. "
            "Nhận tại quầy: dang_giu, hoan_thanh, da_huy, het_han. Giao hàng: cho_thanh_toan, "
            "cho_xac_nhan, dang_chuan_bi, dang_giao, hoan_thanh, da_huy, giao_that_bai."
        ),
    )
    phuong_thuc_thanh_toan = models.TextField(
        choices=PHUONG_THUC_THANH_TOAN,
        default="tai_quay",
        db_default="tai_quay",
        db_column="phuong_thuc_thanh_toan",
        db_comment="Cách khách trả tiền: tai_quay, cod, chuyen_khoan (VietQR) hoặc momo.",
    )
    trang_thai_thanh_toan = models.TextField(
        choices=TRANG_THAI_THANH_TOAN,
        default="chua_thanh_toan",
        db_default="chua_thanh_toan",
        db_column="trang_thai_thanh_toan",
        db_comment="Kết quả thanh toán do service ghi khi nhận hoặc hoàn tiền.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm khách đặt đơn.",
        db_default=Now(),
    )
    thoi_diem_het_giu = models.DateTimeField(
        db_column="thoi_diem_het_giu",
        db_comment=(
            "Hạn của lượng giữ hàng: 24 giờ với đơn nhận tại quầy hoặc chờ xác nhận, "
            "30 phút với đơn chờ thanh toán trực tuyến."
        ),
    )
    tien_hang = _tien(
        "tien_hang", "Tổng thành tiền các dòng sau khuyến mãi", default=0, db_default=0
    )
    giam_gia_thanh_vien = _tien(
        "giam_gia_thanh_vien", "Giảm theo hạng thành viên khi đặt", default=0, db_default=0
    )
    phi_giao_hang = _tien("phi_giao_hang", "Phí giao theo quãng đường", default=0, db_default=0)
    tong_thanh_toan = _tien(
        "tong_thanh_toan",
        "Số tiền khách phải trả, bằng tiền hàng trừ giảm giá cộng phí giao",
        default=0,
        db_default=0,
    )
    ten_nguoi_nhan = models.TextField(
        blank=True,
        db_default="",
        db_column="ten_nguoi_nhan",
        db_comment="Người nhận chụp từ sổ địa chỉ khi đặt giao hàng; rỗng khi nhận tại quầy.",
    )
    so_dien_thoai_nhan = models.TextField(
        blank=True,
        db_default="",
        db_column="so_dien_thoai_nhan",
        db_comment="Số điện thoại người nhận khi giao hàng; rỗng khi nhận tại quầy.",
    )
    dia_chi_giao = models.TextField(
        blank=True,
        db_default="",
        db_column="dia_chi_giao",
        db_comment="Địa chỉ giao chụp khi đặt; sửa sổ địa chỉ sau đó không đổi đơn.",
    )
    vi_tri_giao = PointField(
        geography=True,
        srid=4326,
        null=True,
        blank=True,
        db_column="vi_tri_giao",
        db_comment="Tọa độ giao WGS84 chụp khi đặt; NULL khi nhận tại quầy.",
    )
    khoang_cach_met = models.IntegerField(
        null=True,
        blank=True,
        db_column="khoang_cach_met",
        db_comment="Quãng đường từ chi nhánh tới điểm giao theo OSRM, mét; NULL khi nhận tại quầy.",
    )
    ghi_chu_khach = models.TextField(
        blank=True,
        db_default="",
        db_column="ghi_chu_khach",
        db_comment="Lời nhắn của khách cho nhà thuốc hoặc người giao; một dòng, có thể rỗng.",
    )

    class Meta:
        db_table = "don_hang"
        db_table_comment = (
            "Mỗi hàng là một đơn của khách ở một chi nhánh: đặt giữ nhận tại quầy hoặc giao hàng."
        )
        verbose_name = "đơn hàng"
        ordering = ["-id_don_hang"]
        indexes = [
            models.Index(
                fields=["trang_thai", "thoi_diem_het_giu"],
                name=ten_rang_buoc("chi_muc", "don_hang", "trang_thai", "thoi_diem_het_giu"),
            )
        ]
        constraints = [
            *rang_buoc_van_ban("don_hang", "ma_don_hang"),
            models.UniqueConstraint(
                fields=["ma_don_hang"], name=ten_rang_buoc("duy_nhat", "don_hang", "ma_don_hang")
            ),
            models.CheckConstraint(
                condition=Q(trang_thai__in=_ma(TRANG_THAI_DON)),
                name="kiem_tra__don_hang__trang_thai_hop_le",
            ),
            models.CheckConstraint(
                condition=Q(hinh_thuc_nhan__in=_ma(HINH_THUC_NHAN)),
                name="kiem_tra__don_hang__hinh_thuc_nhan_hop_le",
            ),
            models.CheckConstraint(
                condition=Q(phuong_thuc_thanh_toan__in=_ma(PHUONG_THUC_THANH_TOAN)),
                name="kiem_tra__don_hang__phuong_thuc_hop_le",
            ),
            models.CheckConstraint(
                condition=Q(trang_thai_thanh_toan__in=_ma(TRANG_THAI_THANH_TOAN)),
                name="kiem_tra__don_hang__trang_thai_thanh_toan_hop_le",
            ),
            models.CheckConstraint(
                condition=Q(thoi_diem_het_giu__gt=F("thoi_diem_tao")),
                name="kiem_tra__don_hang__het_giu_sau_khi_tao",
            ),
            models.CheckConstraint(
                condition=Q(
                    hinh_thuc_nhan="nhan_tai_quay",
                    phuong_thuc_thanh_toan="tai_quay",
                    trang_thai__in=TRANG_THAI_NHAN_TAI_QUAY,
                    ten_nguoi_nhan="",
                    so_dien_thoai_nhan="",
                    dia_chi_giao="",
                    vi_tri_giao__isnull=True,
                    khoang_cach_met__isnull=True,
                    phi_giao_hang=0,
                )
                | Q(
                    hinh_thuc_nhan="giao_hang",
                    phuong_thuc_thanh_toan__in=["cod", "chuyen_khoan", "momo"],
                    trang_thai__in=TRANG_THAI_GIAO_HANG,
                    ten_nguoi_nhan__gt="",
                    so_dien_thoai_nhan__gt="",
                    dia_chi_giao__gt="",
                    vi_tri_giao__isnull=False,
                    khoang_cach_met__gte=0,
                ),
                name="kiem_tra__don_hang__du_lieu_dung_hinh_thuc_nhan",
            ),
            *rang_buoc_so("don_hang", "tien_hang", tien=True),
            *rang_buoc_so("don_hang", "giam_gia_thanh_vien", tien=True),
            *rang_buoc_so("don_hang", "phi_giao_hang", tien=True),
            *rang_buoc_so("don_hang", "tong_thanh_toan", tien=True),
            models.CheckConstraint(
                condition=Q(
                    tong_thanh_toan=F("tien_hang") - F("giam_gia_thanh_vien") + F("phi_giao_hang")
                )
                & Q(giam_gia_thanh_vien__lte=F("tien_hang")),
                name="kiem_tra__don_hang__tong_dung_cong_thuc",
            ),
            *rang_buoc_van_ban("don_hang", "ten_nguoi_nhan", rong=True, nhan="ten_nguoi_nhan"),
            *rang_buoc_van_ban(
                "don_hang",
                "so_dien_thoai_nhan",
                rong=True,
                dinh_dang=f"^({SO_DIEN_THOAI[1:-1]})?$",
            ),
            *rang_buoc_van_ban("don_hang", "dia_chi_giao", rong=True),
            *rang_buoc_van_ban("don_hang", "ghi_chu_khach", rong=True),
        ]

    def __str__(self):
        return str(self.ma_don_hang)

    @property
    def la_giao_hang(self):
        return self.hinh_thuc_nhan == "giao_hang"


class ChiTietDonHang(models.Model):
    id_chi_tiet_don_hang = models.BigAutoField(
        db_column="id_chi_tiet_don_hang",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    don_hang = models.ForeignKey(
        "ban_hang.DonHang",
        on_delete=models.PROTECT,
        related_name="cac_dong",
        db_index=False,
        db_column="id_don_hang",
        db_comment="Đơn sở hữu dòng.",
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
    gia_niem_yet = _tien("gia_niem_yet", "Giá niêm yết một đơn vị cơ sở lúc đặt", default=0)
    phan_tram_giam = models.SmallIntegerField(
        default=0,
        db_default=0,
        db_column="phan_tram_giam",
        db_comment="Phần trăm khuyến mãi áp dụng lúc đặt, 0 khi không có.",
    )
    don_gia = _tien("don_gia", "Giá một đơn vị cơ sở sau khuyến mãi lúc đặt", default=0)

    class Meta:
        db_table = "chi_tiet_don_hang"
        db_table_comment = "Mỗi hàng là một thuốc trong đơn, kèm giá chụp lúc đặt."
        verbose_name = "chi tiết đơn hàng"
        ordering = ["id_chi_tiet_don_hang"]
        constraints = [
            *rang_buoc_so("chi_tiet_don_hang", "so_luong", duong=True, tien=False),
            *rang_buoc_so("chi_tiet_don_hang", "gia_niem_yet", tien=True),
            *rang_buoc_so("chi_tiet_don_hang", "don_gia", tien=True),
            models.CheckConstraint(
                condition=Q(phan_tram_giam__gte=0, phan_tram_giam__lte=90)
                & Q(don_gia__lte=F("gia_niem_yet")),
                name=ten_rang_buoc("kiem_tra", "chi_tiet_don_hang", "giam_gia_hop_le"),
            ),
            models.UniqueConstraint(
                fields=["don_hang", "thuoc"],
                name=ten_rang_buoc("duy_nhat", "chi_tiet_don_hang", "id_don_hang", "id_thuoc"),
            ),
        ]

    @property
    def thanh_tien(self):
        return self.don_gia * self.so_luong


class PhanBoDonHang(models.Model):
    id_phan_bo_don_hang = models.BigAutoField(
        db_column="id_phan_bo_don_hang",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    chi_tiet_don_hang = models.ForeignKey(
        "ban_hang.ChiTietDonHang",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_chi_tiet_don_hang",
        db_comment="Dòng đơn được giữ hàng.",
    )
    ton_kho = models.ForeignKey(
        "kho.TonKho",
        on_delete=models.PROTECT,
        db_column="id_ton_kho",
        db_comment="Hàng tồn của lô tại chi nhánh đơn.",
    )
    so_luong = models.IntegerField(
        db_column="so_luong",
        db_comment="Lượng cơ sở đang giữ; giới hạn số nguyên PostgreSQL 32 bit.",
    )

    class Meta:
        db_table = "phan_bo_don_hang"
        db_table_comment = (
            "Mỗi hàng là lượng một dòng đơn giữ trên hàng tồn của một lô theo FEFO; "
            "chỉ tính khi đơn ở trạng thái giữ và chưa quá hạn."
        )
        verbose_name = "phân bổ đơn hàng"
        constraints = [
            *rang_buoc_so("phan_bo_don_hang", "so_luong", duong=True, tien=False),
            models.UniqueConstraint(
                fields=["chi_tiet_don_hang", "ton_kho"],
                name=ten_rang_buoc(
                    "duy_nhat", "phan_bo_don_hang", "id_chi_tiet_don_hang", "id_ton_kho"
                ),
            ),
        ]


class LichSuDonHang(models.Model):
    id_lich_su_don_hang = models.BigAutoField(
        db_column="id_lich_su_don_hang",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    don_hang = models.ForeignKey(
        "ban_hang.DonHang",
        on_delete=models.PROTECT,
        related_name="cac_lich_su",
        db_index=False,
        db_column="id_don_hang",
        db_comment="Đơn được đổi trạng thái.",
    )
    tu_trang_thai = models.TextField(
        choices=TRANG_THAI_DON,
        null=True,
        blank=True,
        db_column="tu_trang_thai",
        db_comment="Trạng thái trước khi đổi; NULL ở dòng tạo đơn.",
    )
    den_trang_thai = models.TextField(
        choices=TRANG_THAI_DON, db_column="den_trang_thai", db_comment="Trạng thái sau khi đổi."
    )
    nguoi_thuc_hien = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="id_tai_khoan_thuc_hien",
        db_comment="Khách hoặc nhân viên thao tác; NULL khi hệ thống tự đổi do quá hạn.",
    )
    ghi_chu = models.TextField(
        blank=True,
        db_default="",
        db_column="ghi_chu",
        db_comment="Lý do hoặc ghi chú hiển thị cho khách; một dòng, có thể rỗng.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_default=Now(), db_column="thoi_diem_tao", db_comment="Thời điểm đổi trạng thái."
    )

    class Meta:
        db_table = "lich_su_don_hang"
        db_table_comment = "Mỗi hàng là một lần đơn đổi trạng thái; không sửa, không xóa."
        verbose_name = "lịch sử đơn hàng"
        ordering = ["thoi_diem_tao", "id_lich_su_don_hang"]
        indexes = [
            models.Index(
                fields=["don_hang", "thoi_diem_tao"],
                name=ten_rang_buoc("chi_muc", "lich_su_don_hang", "id_don_hang", "thoi_diem_tao"),
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(tu_trang_thai__isnull=True) | Q(tu_trang_thai__in=_ma(TRANG_THAI_DON)),
                name=ten_rang_buoc("kiem_tra", "lich_su_don_hang", "tu_trang_thai_hop_le"),
            ),
            models.CheckConstraint(
                condition=Q(den_trang_thai__in=_ma(TRANG_THAI_DON)),
                name=ten_rang_buoc("kiem_tra", "lich_su_don_hang", "den_trang_thai_hop_le"),
            ),
            *rang_buoc_van_ban("lich_su_don_hang", "ghi_chu", rong=True),
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
    don_hang = models.ForeignKey(
        "ban_hang.DonHang",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_don_hang",
        db_comment="Đơn của khách được xuất kho; NULL nghĩa là bán trực tiếp tại quầy.",
        null=True,
        blank=True,
    )
    da_kiem_tra_don_thuoc = models.BooleanField(
        default=False,
        db_default=False,
        db_column="da_kiem_tra_don_thuoc",
        db_comment=(
            "Dược sĩ xác nhận đã kiểm tra đơn thuốc của bác sĩ; bắt buộc khi phiếu có "
            "thuốc kê đơn, service kiểm trước khi lập phiếu."
        ),
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "phieu_ban"
        db_table_comment = (
            "Mỗi hàng là một lần xuất kho bán: bán trực tiếp, giao đơn nhận tại quầy "
            "hoặc chuẩn bị đơn giao hàng."
        )
        verbose_name = "phiếu bán"
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
                fields=["don_hang"],
                name=ten_rang_buoc("duy_nhat", "phieu_ban", "id_don_hang"),
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


LY_DO_HOAN_KHO = [("giao_that_bai", "Giao hàng thất bại"), ("huy_don", "Hủy đơn đã xuất kho")]


class PhieuHoanKho(models.Model):
    id_phieu_hoan_kho = models.BigAutoField(
        db_column="id_phieu_hoan_kho",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ma_phieu_hoan_kho = models.TextField(
        db_column="ma_phieu_hoan_kho", db_comment="Mã phiếu hệ thống cấp; văn bản một dòng."
    )
    phieu_ban = models.ForeignKey(
        "ban_hang.PhieuBan",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_phieu_ban",
        db_comment="Phiếu bán của đơn mà hàng chưa tới tay khách nên nhập lại.",
    )
    nguoi_lap = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        on_delete=models.PROTECT,
        db_column="id_tai_khoan_lap",
        db_comment="Nhân viên xác nhận hàng đã về kho.",
    )
    ly_do = models.TextField(
        choices=LY_DO_HOAN_KHO,
        db_column="ly_do",
        db_comment="giao_that_bai hoặc huy_don; hàng còn nguyên niêm phong nên bán lại được.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_default=Now(), db_column="thoi_diem_tao", db_comment="Thời điểm nhập lại kho."
    )

    class Meta:
        db_table = "phieu_hoan_kho"
        db_table_comment = (
            "Mỗi hàng là một lần nhập lại toàn bộ hàng của phiếu bán chưa giao được, "
            "trả về đúng lô đã xuất."
        )
        verbose_name = "phiếu hoàn kho"
        constraints = [
            *rang_buoc_van_ban("phieu_hoan_kho", "ma_phieu_hoan_kho"),
            models.UniqueConstraint(
                fields=["ma_phieu_hoan_kho"],
                name=ten_rang_buoc("duy_nhat", "phieu_hoan_kho", "ma_phieu_hoan_kho"),
            ),
            models.UniqueConstraint(
                fields=["phieu_ban"],
                name=ten_rang_buoc("duy_nhat", "phieu_hoan_kho", "id_phieu_ban"),
            ),
            models.CheckConstraint(
                condition=Q(ly_do__in=_ma(LY_DO_HOAN_KHO)),
                name=ten_rang_buoc("kiem_tra", "phieu_hoan_kho", "ly_do_hop_le"),
            ),
        ]

    def __str__(self):
        return str(self.ma_phieu_hoan_kho)


class ChiTietPhieuHoanKho(models.Model):
    id_chi_tiet_phieu_hoan_kho = models.BigAutoField(
        db_column="id_chi_tiet_phieu_hoan_kho",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    phieu_hoan_kho = models.ForeignKey(
        "ban_hang.PhieuHoanKho",
        on_delete=models.PROTECT,
        db_column="id_phieu_hoan_kho",
        db_comment="Phiếu hoàn kho sở hữu dòng.",
    )
    phan_bo_phieu_ban = models.ForeignKey(
        "ban_hang.PhanBoPhieuBan",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_phan_bo_phieu_ban",
        db_comment="Lượng đã xuất từ một lô; hàng trả về đúng hàng tồn của phân bổ này.",
    )
    so_luong = models.IntegerField(
        db_column="so_luong",
        db_comment="Lượng cơ sở nhập lại; giới hạn số nguyên PostgreSQL 32 bit.",
    )

    class Meta:
        db_table = "chi_tiet_phieu_hoan_kho"
        db_table_comment = "Mỗi hàng là lượng nhập lại cho một phân bổ xuất của phiếu bán."
        verbose_name = "chi tiết phiếu hoàn kho"
        constraints = [
            *rang_buoc_so("chi_tiet_phieu_hoan_kho", "so_luong", duong=True),
            models.UniqueConstraint(
                fields=["phan_bo_phieu_ban"],
                name=ten_rang_buoc("duy_nhat", "chi_tiet_phieu_hoan_kho", "id_phan_bo_phieu_ban"),
            ),
        ]
