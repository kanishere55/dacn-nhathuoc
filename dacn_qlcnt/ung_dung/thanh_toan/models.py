from django.db import models
from django.db.models import Q
from django.db.models.functions import Now

from ung_dung.chung.ten_csdl import rang_buoc_so, rang_buoc_van_ban, ten_rang_buoc

# Mã do ngân hàng/cổng cấp (số giao dịch SePay, transId MoMo, mã FT...).
MA_THAM_CHIEU = r"^[A-Za-z0-9._:/-]{1,64}$"

BANG = "giao_dich_thanh_toan"
LOAI_GIAO_DICH = [("thu", "Thu tiền"), ("hoan", "Hoàn tiền")]
PHUONG_THUC = [
    ("tien_mat", "Tiền mặt"),
    ("chuyen_khoan", "Chuyển khoản"),
    ("cod", "Thu hộ khi giao (COD)"),
    ("momo", "Ví MoMo"),
]
TRANG_THAI = [
    ("cho", "Đang chờ"),
    ("thanh_cong", "Thành công"),
    ("that_bai", "Thất bại"),
    ("het_han", "Hết hạn"),
]


def _ma(cac):
    return [ma for ma, _ in cac]


class GiaoDichThanhToan(models.Model):
    id_giao_dich_thanh_toan = models.BigAutoField(
        primary_key=True,
        db_column="id_giao_dich_thanh_toan",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
    )
    ma_giao_dich_thanh_toan = models.TextField(
        db_column="ma_giao_dich_thanh_toan",
        db_comment="Mã giao dịch hệ thống cấp, gửi cho cổng thanh toán làm mã tham chiếu.",
    )
    don_hang = models.ForeignKey(
        "ban_hang.DonHang",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cac_giao_dich",
        db_column="id_don_hang",
        db_comment="Đơn được thu hoặc hoàn tiền; NULL khi là phiếu bán trực tiếp tại quầy.",
    )
    phieu_ban = models.ForeignKey(
        "ban_hang.PhieuBan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cac_giao_dich",
        db_column="id_phieu_ban",
        db_comment="Phiếu bán được thu tiền tại quầy; NULL với thanh toán trực tuyến trước khi xuất kho.",
    )
    loai_giao_dich = models.TextField(
        choices=LOAI_GIAO_DICH,
        db_column="loai_giao_dich",
        db_comment="thu: khách trả tiền; hoan: nhà thuốc trả lại tiền cho khách.",
    )
    phuong_thuc = models.TextField(
        choices=PHUONG_THUC,
        db_column="phuong_thuc",
        db_comment="Kênh nhận hoặc trả tiền: tien_mat, chuyen_khoan, cod, momo.",
    )
    so_tien = models.DecimalField(
        max_digits=14,
        decimal_places=0,
        db_column="so_tien",
        db_comment="Số tiền của giao dịch; VND nguyên dương, tối đa 14 chữ số.",
    )
    trang_thai = models.TextField(
        choices=TRANG_THAI,
        default="cho",
        db_default="cho",
        db_column="trang_thai",
        db_comment="cho khi chờ cổng xác nhận; thanh_cong, that_bai hoặc het_han khi đã kết thúc.",
    )
    ma_tham_chieu = models.TextField(
        null=True,
        blank=True,
        db_column="ma_tham_chieu",
        db_comment=(
            "Mã giao dịch phía ngân hàng, SePay hoặc MoMo; duy nhất theo phương thức để webhook "
            "gửi lại không ghi hai lần. NULL khi chưa có hoặc tiền mặt."
        ),
    )
    ghi_chu = models.TextField(
        blank=True,
        db_default="",
        db_column="ghi_chu",
        db_comment="Ghi chú một dòng: nội dung chuyển khoản nhận được hoặc lời nhân viên.",
    )
    nguoi_xac_nhan = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="id_tai_khoan_xac_nhan",
        db_comment="Nhân viên ghi nhận; NULL khi cổng thanh toán tự xác nhận.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_default=Now(), db_column="thoi_diem_tao", db_comment="Thời điểm tạo giao dịch."
    )
    thoi_diem_hoan_tat = models.DateTimeField(
        null=True,
        blank=True,
        db_column="thoi_diem_hoan_tat",
        db_comment="Thời điểm giao dịch kết thúc; NULL khi còn chờ.",
    )

    class Meta:
        db_table = BANG
        db_table_comment = "Mỗi hàng là một lần thu hoặc hoàn tiền của đơn hàng hay phiếu bán."
        verbose_name = "giao dịch thanh toán"
        ordering = ["-thoi_diem_tao", "-id_giao_dich_thanh_toan"]
        constraints = [
            *rang_buoc_van_ban(BANG, "ma_giao_dich_thanh_toan"),
            models.UniqueConstraint(
                fields=["ma_giao_dich_thanh_toan"],
                name=ten_rang_buoc("duy_nhat", BANG, "ma_giao_dich_thanh_toan"),
            ),
            models.UniqueConstraint(
                fields=["phuong_thuc", "ma_tham_chieu"],
                name=ten_rang_buoc("duy_nhat", BANG, "phuong_thuc", "ma_tham_chieu"),
            ),
            models.CheckConstraint(
                condition=Q(don_hang__isnull=False) | Q(phieu_ban__isnull=False),
                name=ten_rang_buoc("kiem_tra", BANG, "co_chung_tu"),
            ),
            models.CheckConstraint(
                condition=Q(loai_giao_dich__in=_ma(LOAI_GIAO_DICH)),
                name=ten_rang_buoc("kiem_tra", BANG, "loai_giao_dich_hop_le"),
            ),
            models.CheckConstraint(
                condition=Q(phuong_thuc__in=_ma(PHUONG_THUC)),
                name=ten_rang_buoc("kiem_tra", BANG, "phuong_thuc_hop_le"),
            ),
            models.CheckConstraint(
                condition=Q(trang_thai__in=_ma(TRANG_THAI)),
                name=ten_rang_buoc("kiem_tra", BANG, "trang_thai_hop_le"),
            ),
            models.CheckConstraint(
                condition=Q(trang_thai="cho", thoi_diem_hoan_tat__isnull=True)
                | (~Q(trang_thai="cho") & Q(thoi_diem_hoan_tat__isnull=False)),
                name=ten_rang_buoc("kiem_tra", BANG, "hoan_tat_dung_trang_thai"),
            ),
            *rang_buoc_so(BANG, "so_tien", duong=True, tien=True),
            *rang_buoc_van_ban(
                BANG, "ma_tham_chieu", dinh_dang=MA_THAM_CHIEU, nhan="ma_tham_chieu"
            ),
            *rang_buoc_van_ban(BANG, "ghi_chu", rong=True),
        ]

    def __str__(self):
        return str(self.ma_giao_dich_thanh_toan)
