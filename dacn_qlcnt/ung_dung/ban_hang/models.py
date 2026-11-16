from zoneinfo import ZoneInfo

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now, TruncDate

from ung_dung.chung.ten_csdl import (
    EMAIL,
    rang_buoc_so,
    rang_buoc_van_ban,
    ten_rang_buoc,
)

# Đơn đặt giữ theo đề cương: khách đặt trên website, nhận và trả tiền tại quầy của chi nhánh.
TRANG_THAI_DON = [
    ("dang_giu", "Đang giữ hàng"),
    ("hoan_thanh", "Đã nhận hàng"),
    ("da_huy", "Đã hủy"),
    ("het_han", "Hết hạn giữ"),
]
# Lượng giữ chỉ có hiệu lực ở trạng thái này và trước thoi_diem_het_giu.
TRANG_THAI_GIU = ("dang_giu",)
# Khách trả tiền tại quầy khi nhận đơn hoặc khi mua trực tiếp.
PHUONG_THUC_TAI_QUAY = [("tien_mat", "Tiền mặt"), ("chuyen_khoan", "Chuyển khoản")]


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
        db_comment="Chi nhánh duy nhất giữ hàng, nơi khách đến nhận và trả tiền.",
    )
    trang_thai = models.TextField(
        choices=TRANG_THAI_DON,
        default="dang_giu",
        db_default="dang_giu",
        db_column="trang_thai",
        db_comment=(
            "Trạng thái xử lý; chỉ service đổi theo bảng chuyển hợp lệ và ghi lich_su_don_hang: "
            "dang_giu, hoan_thanh (khách đã nhận và trả tiền tại quầy), da_huy, het_han."
        ),
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm khách đặt đơn.",
        db_default=Now(),
    )
    thoi_diem_het_giu = models.DateTimeField(
        db_column="thoi_diem_het_giu",
        db_comment="Hạn của lượng giữ hàng, 24 giờ sau khi đặt; quá hạn thì đơn hết hạn.",
    )
    tien_hang = _tien(
        "tien_hang", "Tổng thành tiền các dòng sau khuyến mãi", default=0, db_default=0
    )
    giam_gia_thanh_vien = _tien(
        "giam_gia_thanh_vien", "Giảm theo hạng thành viên khi đặt", default=0, db_default=0
    )
    tong_thanh_toan = _tien(
        "tong_thanh_toan",
        "Số tiền khách trả tại quầy, bằng tiền hàng trừ giảm giá thành viên",
        default=0,
        db_default=0,
    )
    ghi_chu_khach = models.TextField(
        blank=True,
        db_default="",
        db_column="ghi_chu_khach",
        db_comment="Lời nhắn của khách cho nhà thuốc; một dòng, có thể rỗng.",
    )

    class Meta:
        db_table = "don_hang"
        db_table_comment = (
            "Mỗi hàng là một đơn đặt giữ của khách ở một chi nhánh; khách nhận và trả tiền "
            "tại quầy."
        )
        verbose_name = "đơn đặt giữ"
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
                condition=Q(thoi_diem_het_giu__gt=F("thoi_diem_tao")),
                name="kiem_tra__don_hang__het_giu_sau_khi_tao",
            ),
            *rang_buoc_so("don_hang", "tien_hang", tien=True),
            *rang_buoc_so("don_hang", "giam_gia_thanh_vien", tien=True),
            *rang_buoc_so("don_hang", "tong_thanh_toan", tien=True),
            models.CheckConstraint(
                condition=Q(tong_thanh_toan=F("tien_hang") - F("giam_gia_thanh_vien"))
                & Q(giam_gia_thanh_vien__lte=F("tien_hang")),
                name="kiem_tra__don_hang__tong_dung_cong_thuc",
            ),
            *rang_buoc_van_ban("don_hang", "ghi_chu_khach", rong=True),
        ]

    def __str__(self):
        return str(self.ma_don_hang)

    @property
    def nhan_thanh_toan_khach(self):
        """Tình trạng tiền theo cách khách hiểu (trang đơn của khách, email)."""
        return {
            "dang_giu": "Trả tại quầy khi nhận hàng",
            "hoan_thanh": "Đã thanh toán tại quầy",
        }.get(self.trang_thai, "Không phát sinh thanh toán")

    @property
    def lop_nhan_thanh_toan_khach(self):
        return {"dang_giu": "chua_thanh_toan", "hoan_thanh": "da_thanh_toan"}.get(
            self.trang_thai, "khong_thu"
        )


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
    giam_gia_phan_bo = _tien(
        "giam_gia_phan_bo",
        "Phần giảm theo hạng thành viên của đơn phân bổ cho dòng theo tỷ lệ thành tiền, phần lẻ "
        "dồn vào dòng cuối; dòng thuốc kê đơn luôn 0. Tổng các dòng bằng giam_gia_thanh_vien",
        default=0,
        db_default=0,
    )

    class Meta:
        db_table = "chi_tiet_don_hang"
        db_table_comment = "Mỗi hàng là một thuốc trong đơn, kèm giá chụp lúc đặt."
        verbose_name = "chi tiết đơn hàng"
        ordering = ["id_chi_tiet_don_hang"]
        constraints = [
            *rang_buoc_so("chi_tiet_don_hang", "so_luong", duong=True, tien=False),
            *rang_buoc_so("chi_tiet_don_hang", "gia_niem_yet", tien=True),
            *rang_buoc_so("chi_tiet_don_hang", "don_gia", tien=True),
            *rang_buoc_so("chi_tiet_don_hang", "giam_gia_phan_bo", tien=True),
            models.CheckConstraint(
                condition=Q(giam_gia_phan_bo__lte=F("so_luong") * F("don_gia")),
                name=ten_rang_buoc("kiem_tra", "chi_tiet_don_hang", "giam_khong_vuot_thanh_tien"),
            ),
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

    @property
    def thuc_tra(self):
        """Số tiền khách thực trả cho dòng: thành tiền trừ phần ưu đãi thành viên của dòng."""
        return self.thanh_tien - self.giam_gia_phan_bo


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


# Mã đơn điện tử dạng <mã cơ sở><số đơn>-<loại đơn>; cho phép cả mã nội bộ của bệnh viện.
MA_DON_THUOC = r"^[A-Za-z0-9][A-Za-z0-9-]{5,29}$"


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
        db_comment="Đơn đặt giữ khách đến nhận; NULL nghĩa là bán trực tiếp tại quầy.",
        null=True,
        blank=True,
    )
    phuong_thuc_thanh_toan = models.TextField(
        choices=PHUONG_THUC_TAI_QUAY,
        default="tien_mat",
        db_default="tien_mat",
        db_column="phuong_thuc_thanh_toan",
        db_comment=(
            "Cách khách trả tiền tại quầy: tien_mat hoặc chuyen_khoan; nhân viên lập phiếu xác "
            "nhận đã nhận đủ tiền."
        ),
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
    ma_don_thuoc = models.TextField(
        db_column="ma_don_thuoc",
        db_comment=(
            "Mã đơn thuốc điện tử in trên đơn (liên thông đơn thuốc quốc gia); NULL khi đơn "
            "giấy không có mã hoặc phiếu không có thuốc kê đơn."
        ),
        null=True,
        blank=True,
    )
    ten_nguoi_ke_don = models.TextField(
        db_column="ten_nguoi_ke_don",
        db_comment="Họ tên bác sĩ kê đơn; rỗng khi phiếu không có thuốc kê đơn.",
        default="",
        db_default="",
        blank=True,
    )
    noi_kham_benh = models.TextField(
        db_column="noi_kham_benh",
        db_comment="Cơ sở khám bệnh, chữa bệnh phát hành đơn; rỗng khi không có thuốc kê đơn.",
        default="",
        db_default="",
        blank=True,
    )
    ngay_ke_don = models.DateField(
        null=True,
        blank=True,
        db_column="ngay_ke_don",
        db_comment=(
            "Ngày bác sĩ kê đơn, không sau ngày bán; NULL khi phiếu không có thuốc kê đơn và ở "
            "phiếu lập trước khi bổ sung cột. Service bắt buộc ghi với phiếu mới có thuốc kê đơn."
        ),
    )
    ho_ten_nguoi_benh = models.TextField(
        default="",
        db_default="",
        blank=True,
        db_column="ho_ten_nguoi_benh",
        db_comment=(
            "Họ tên người bệnh ghi trên đơn thuốc, đi cùng ngày kê đơn; rỗng khi không có "
            "thuốc kê đơn hoặc phiếu lập trước khi bổ sung cột."
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
            "Mỗi hàng là một lần bán tại quầy kèm xuất kho: bán trực tiếp hoặc giao đơn đặt giữ "
            "cho khách đến nhận."
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
            models.CheckConstraint(
                condition=Q(phuong_thuc_thanh_toan__in=_ma(PHUONG_THUC_TAI_QUAY)),
                name=ten_rang_buoc("kiem_tra", "phieu_ban", "phuong_thuc_thanh_toan_hop_le"),
            ),
            *rang_buoc_van_ban(
                "phieu_ban", "ma_don_thuoc", dinh_dang=MA_DON_THUOC, nhan="ma_don_thuoc"
            ),
            *rang_buoc_van_ban("phieu_ban", "ten_nguoi_ke_don", rong=True, nhan="nguoi_ke_don"),
            *rang_buoc_van_ban("phieu_ban", "noi_kham_benh", rong=True),
            *rang_buoc_van_ban("phieu_ban", "ho_ten_nguoi_benh", rong=True),
            # Đã kiểm tra đơn thì phải ghi người kê và nơi kê; chưa kiểm tra thì để trống hết.
            models.CheckConstraint(
                condition=(
                    Q(da_kiem_tra_don_thuoc=True) & ~Q(ten_nguoi_ke_don="") & ~Q(noi_kham_benh="")
                )
                | Q(
                    da_kiem_tra_don_thuoc=False,
                    ten_nguoi_ke_don="",
                    noi_kham_benh="",
                    ma_don_thuoc__isnull=True,
                    ngay_ke_don__isnull=True,
                    ho_ten_nguoi_benh="",
                ),
                name=ten_rang_buoc("kiem_tra", "phieu_ban", "don_thuoc_du_thong_tin"),
            ),
            # Ngày kê đơn và người bệnh đi cùng nhau; đơn không thể kê sau ngày bán.
            models.CheckConstraint(
                condition=Q(ngay_ke_don__isnull=True, ho_ten_nguoi_benh="")
                | (Q(ngay_ke_don__isnull=False) & ~Q(ho_ten_nguoi_benh="")),
                name=ten_rang_buoc("kiem_tra", "phieu_ban", "ngay_ke_don_co_nguoi_benh"),
            ),
            models.CheckConstraint(
                condition=Q(ngay_ke_don__isnull=True)
                | Q(
                    ngay_ke_don__lte=TruncDate("thoi_diem_tao", tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
                ),
                name=ten_rang_buoc("kiem_tra", "phieu_ban", "ngay_ke_don_khong_sau_ngay_ban"),
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
    giam_gia_phan_bo = _tien(
        "giam_gia_phan_bo",
        "Ưu đãi thành viên của dòng chép từ dòng đơn khi xuất kho cho đơn; 0 khi bán trực tiếp. "
        "Doanh thu dòng sau ưu đãi bằng so_luong nhân don_gia trừ cột này",
        default=0,
        db_default=0,
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
            *rang_buoc_so("chi_tiet_phieu_ban", "giam_gia_phan_bo", tien=True),
            models.CheckConstraint(
                condition=Q(giam_gia_phan_bo__lte=F("so_luong") * F("don_gia")),
                name=ten_rang_buoc("kiem_tra", "chi_tiet_phieu_ban", "giam_khong_vuot_thanh_tien"),
            ),
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


TRANG_THAI_XUAT_HOA_DON = [
    ("cho_xu_ly", "Chờ xử lý"),
    ("da_xuat", "Đã xuất hóa đơn"),
    ("tu_choi", "Từ chối"),
]
# Mã số thuế doanh nghiệp 10 chữ số; đơn vị phụ thuộc thêm "-" và 3 chữ số.
MA_SO_THUE = r"^[0-9]{10}(-[0-9]{3})?$"
# Ký hiệu mẫu số (1 chữ số) và ký hiệu hóa đơn 6 ký tự theo Thông tư 32/2025/TT-BTC:
# C/K (có mã hoặc không mã của cơ quan thuế), 2 số cuối năm, 1 chữ loại, 2 chữ do người bán đặt.
KY_HIEU_HOA_DON = r"^[1-9][CK][0-9]{2}[A-Z]{3}$"
# Số hóa đơn tối đa 8 chữ số (Nghị định 123/2020/NĐ-CP Điều 10).
SO_HOA_DON = r"^[0-9]{1,8}$"


class YeuCauXuatHoaDon(models.Model):
    id_yeu_cau_xuat_hoa_don = models.BigAutoField(
        primary_key=True,
        db_column="id_yeu_cau_xuat_hoa_don",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
    )
    don_hang = models.ForeignKey(
        "ban_hang.DonHang",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_don_hang",
        db_comment=(
            "Đơn cần hóa đơn đứng tên doanh nghiệp, gửi từ lúc đặt tới hết tháng nhận hàng; "
            "mỗi đơn một yêu cầu."
        ),
    )
    ten_cong_ty = models.TextField(
        db_column="ten_cong_ty", db_comment="Tên doanh nghiệp theo đăng ký thuế; một dòng."
    )
    ma_so_thue = models.TextField(
        db_column="ma_so_thue",
        db_comment="Mã số thuế 10 chữ số, đơn vị phụ thuộc thêm -XXX.",
    )
    dia_chi_cong_ty = models.TextField(
        db_column="dia_chi_cong_ty", db_comment="Địa chỉ trụ sở theo đăng ký thuế; một dòng."
    )
    email_nhan_hoa_don = models.TextField(
        db_column="email_nhan_hoa_don",
        db_comment="Email nhận hóa đơn điện tử; chữ thường.",
    )
    trang_thai = models.TextField(
        choices=TRANG_THAI_XUAT_HOA_DON,
        default="cho_xu_ly",
        db_default="cho_xu_ly",
        db_column="trang_thai",
        db_comment="cho_xu_ly: chờ nhân viên; da_xuat: đã phát hành ngoài hệ thống; tu_choi.",
    )
    ghi_chu_xu_ly = models.TextField(
        default="",
        db_default="",
        blank=True,
        db_column="ghi_chu_xu_ly",
        db_comment=(
            "Câu tóm tắt kết quả gửi khách (ký hiệu và số hóa đơn, hoặc lý do từ chối); "
            "rỗng khi chờ xử lý."
        ),
    )
    ky_hieu_hoa_don = models.TextField(
        default="",
        db_default="",
        blank=True,
        db_column="ky_hieu_hoa_don",
        db_comment=(
            "Ký hiệu mẫu số và ký hiệu hóa đơn điện tử đã phát hành, ví dụ 1C26TAA; "
            "rỗng khi chưa xuất hoặc yêu cầu cũ chỉ có ghi chú."
        ),
    )
    so_hoa_don = models.TextField(
        default="",
        db_default="",
        blank=True,
        db_column="so_hoa_don",
        db_comment="Số hóa đơn điện tử, 1 đến 8 chữ số; rỗng khi chưa xuất hoặc yêu cầu cũ.",
    )
    ly_do_tu_choi = models.TextField(
        default="",
        db_default="",
        blank=True,
        db_column="ly_do_tu_choi",
        db_comment="Lý do không xuất hóa đơn công ty; chỉ có khi từ chối.",
    )
    nguoi_xu_ly = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="id_tai_khoan_xu_ly",
        db_comment="Nhân sự chi nhánh của đơn đã xử lý; NULL khi chờ xử lý.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_default=Now(), db_column="thoi_diem_tao", db_comment="Thời điểm khách gửi yêu cầu."
    )
    thoi_diem_xu_ly = models.DateTimeField(
        null=True,
        blank=True,
        db_column="thoi_diem_xu_ly",
        db_comment="Thời điểm xuất hoặc từ chối; NULL khi chờ xử lý.",
    )

    class Meta:
        db_table = "yeu_cau_xuat_hoa_don"
        db_table_comment = (
            "Mỗi hàng là yêu cầu hóa đơn doanh nghiệp cho một đơn; hóa đơn điện tử phát hành "
            "ngoài hệ thống."
        )
        verbose_name = "yêu cầu xuất hóa đơn"
        ordering = ["-thoi_diem_tao", "-id_yeu_cau_xuat_hoa_don"]
        constraints = [
            models.UniqueConstraint(
                fields=["don_hang"],
                name=ten_rang_buoc("duy_nhat", "yeu_cau_xuat_hoa_don", "id_don_hang"),
            ),
            *rang_buoc_van_ban("yeu_cau_xuat_hoa_don", "ten_cong_ty", nhan="ten_cong_ty"),
            *rang_buoc_van_ban(
                "yeu_cau_xuat_hoa_don", "ma_so_thue", dinh_dang=MA_SO_THUE, nhan="ma_so_thue"
            ),
            *rang_buoc_van_ban("yeu_cau_xuat_hoa_don", "dia_chi_cong_ty"),
            *rang_buoc_van_ban("yeu_cau_xuat_hoa_don", "email_nhan_hoa_don", dinh_dang=EMAIL),
            models.CheckConstraint(
                condition=Q(trang_thai__in=_ma(TRANG_THAI_XUAT_HOA_DON)),
                name=ten_rang_buoc("kiem_tra", "yeu_cau_xuat_hoa_don", "trang_thai_hop_le"),
            ),
            *rang_buoc_van_ban("yeu_cau_xuat_hoa_don", "ghi_chu_xu_ly", rong=True, nhieu_dong=True),
            models.CheckConstraint(
                condition=(
                    Q(
                        trang_thai="cho_xu_ly",
                        nguoi_xu_ly__isnull=True,
                        thoi_diem_xu_ly__isnull=True,
                    )
                    | (
                        ~Q(trang_thai="cho_xu_ly")
                        & Q(nguoi_xu_ly__isnull=False, thoi_diem_xu_ly__isnull=False)
                        & ~Q(ghi_chu_xu_ly="")
                    )
                ),
                name=ten_rang_buoc("kiem_tra", "yeu_cau_xuat_hoa_don", "xu_ly_dung_trang_thai"),
            ),
            *rang_buoc_van_ban(
                "yeu_cau_xuat_hoa_don",
                "ky_hieu_hoa_don",
                rong=True,
                dinh_dang=f"^({KY_HIEU_HOA_DON[1:-1]})?$",
            ),
            *rang_buoc_van_ban(
                "yeu_cau_xuat_hoa_don",
                "so_hoa_don",
                rong=True,
                dinh_dang=f"^({SO_HOA_DON[1:-1]})?$",
            ),
            *rang_buoc_van_ban("yeu_cau_xuat_hoa_don", "ly_do_tu_choi", rong=True, nhieu_dong=True),
            # Yêu cầu cũ có thể chỉ có ghi chú. Khi ghi kết quả mới, service yêu cầu đủ cả cặp.
            models.CheckConstraint(
                condition=Q(
                    trang_thai="cho_xu_ly", ky_hieu_hoa_don="", so_hoa_don="", ly_do_tu_choi=""
                )
                | (
                    Q(trang_thai="da_xuat", ly_do_tu_choi="")
                    & (
                        Q(ky_hieu_hoa_don="", so_hoa_don="")
                        | (~Q(ky_hieu_hoa_don="") & ~Q(so_hoa_don=""))
                    )
                )
                | (
                    Q(trang_thai="tu_choi", ky_hieu_hoa_don="", so_hoa_don="")
                    & ~Q(ly_do_tu_choi="")
                ),
                name=ten_rang_buoc("kiem_tra", "yeu_cau_xuat_hoa_don", "ket_qua_dung_trang_thai"),
            ),
            models.UniqueConstraint(
                fields=["ky_hieu_hoa_don", "so_hoa_don"],
                condition=Q(trang_thai="da_xuat") & ~Q(ky_hieu_hoa_don=""),
                name=ten_rang_buoc(
                    "duy_nhat", "yeu_cau_xuat_hoa_don", "ky_hieu_hoa_don", "so_hoa_don"
                ),
            ),
        ]

    def __str__(self):
        return f"{self.don_hang.ma_don_hang} · {self.ten_cong_ty}"
