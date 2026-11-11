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
        db_comment=(
            "Nhân sự ghi nhận tiền: bắt buộc với tiền mặt, COD đã đối soát và mọi khoản hoàn; "
            "NULL khi cổng thanh toán tự xác nhận hoặc khoản COD còn chờ đối soát."
        ),
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
            # COD cũ được ghi nhận tự động lúc giao; service yêu cầu nhân sự với giao dịch mới.
            models.CheckConstraint(
                condition=~Q(
                    phuong_thuc="tien_mat",
                    trang_thai="thanh_cong",
                    nguoi_xac_nhan__isnull=True,
                ),
                name=ten_rang_buoc("kiem_tra", BANG, "tien_mat_co_nguoi_nhan"),
            ),
            # Hoàn tiền là thao tác của nhân sự, ghi khi đã trả xong cho khách.
            models.CheckConstraint(
                condition=~Q(loai_giao_dich="hoan")
                | Q(trang_thai="thanh_cong", nguoi_xac_nhan__isnull=False),
                name=ten_rang_buoc("kiem_tra", BANG, "hoan_thanh_cong_co_nguoi_ghi"),
            ),
        ]

    def __str__(self):
        return str(self.ma_giao_dich_thanh_toan)


BANG_CONG_DEN = "giao_dich_cong_den"
NGUON_CONG_DEN = [("sepay", "SePay (chuyển khoản ngân hàng)"), ("momo", "Ví MoMo")]
TRANG_THAI_CONG_DEN = [
    ("da_khop", "Đã ghi vào đơn"),
    ("cho_khop", "Chưa khớp đơn"),
    ("bo_qua", "Bỏ qua"),
]


class GiaoDichCongDen(models.Model):
    """Dữ liệu gốc mỗi thông báo SePay hoặc MoMo đã qua kiểm khóa, chữ ký."""

    id_giao_dich_cong_den = models.BigAutoField(
        primary_key=True,
        db_column="id_giao_dich_cong_den",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
    )
    nguon = models.TextField(
        choices=NGUON_CONG_DEN,
        db_column="nguon",
        db_comment="Cổng gửi thông báo: sepay hoặc momo.",
    )
    ma_doi_tac = models.TextField(
        db_column="ma_doi_tac",
        db_comment=(
            "Mã định danh thông báo phía cổng (id giao dịch SePay; orderId-transId của MoMo); "
            "duy nhất theo nguồn để thông báo gửi lại chỉ lưu một lần."
        ),
    )
    ma_tham_chieu = models.TextField(
        blank=True,
        db_default="",
        db_column="ma_tham_chieu",
        db_comment="Mã giao dịch ngân hàng (referenceCode của SePay) hoặc transId MoMo; có thể rỗng.",
    )
    so_tai_khoan_nhan = models.TextField(
        blank=True,
        db_default="",
        db_column="so_tai_khoan_nhan",
        db_comment="Số tài khoản nhận tiền trong thông báo SePay; rỗng với MoMo.",
    )
    so_tien = models.DecimalField(
        max_digits=14,
        decimal_places=0,
        db_column="so_tien",
        db_comment="Số tiền trong thông báo; VND nguyên không âm, tối đa 14 chữ số.",
    )
    noi_dung_giao_dich = models.TextField(
        blank=True,
        db_default="",
        db_column="noi_dung_giao_dich",
        db_comment="Nội dung chuyển khoản hoặc lời nhắn của cổng; một dòng, có thể rỗng.",
    )
    du_lieu_goc = models.TextField(
        db_column="du_lieu_goc",
        db_comment="Toàn bộ thân thông báo dạng JSON văn bản để đối soát và khiếu nại.",
    )
    trang_thai = models.TextField(
        choices=TRANG_THAI_CONG_DEN,
        db_column="trang_thai",
        db_comment=(
            "da_khop: đã ghi thành giao dịch của đơn; cho_khop: tiền vào chưa tìm được đơn, chờ "
            "quản lý gán; bo_qua: không phải tiền vào của nhà thuốc hoặc đã xử lý ngoài hệ thống."
        ),
    )
    giao_dich_thanh_toan = models.ForeignKey(
        "thanh_toan.GiaoDichThanhToan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="cong_den",
        db_column="id_giao_dich_thanh_toan",
        db_comment="Giao dịch thu được tạo hoặc khớp từ thông báo; NULL khi chưa khớp hoặc bỏ qua.",
    )
    ghi_chu_xu_ly = models.TextField(
        blank=True,
        db_default="",
        db_column="ghi_chu_xu_ly",
        db_comment="Lý do bỏ qua hoặc ghi chú của quản lý khi gán, hoàn; một dòng.",
    )
    nguoi_xu_ly = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="id_tai_khoan_xu_ly",
        db_comment="Quản lý gán vào đơn hoặc ghi chú bỏ qua; NULL khi hệ thống tự xử lý.",
    )
    thoi_diem_nhan = models.DateTimeField(
        db_default=Now(), db_column="thoi_diem_nhan", db_comment="Thời điểm máy chủ nhận thông báo."
    )

    class Meta:
        db_table = BANG_CONG_DEN
        db_table_comment = (
            "Mỗi hàng là một thông báo thanh toán từ SePay hoặc MoMo đã xác thực, lưu cả dữ liệu "
            "gốc; tiền vào không khớp đơn chờ quản lý xử lý."
        )
        verbose_name = "giao dịch cổng đến"
        ordering = ["-thoi_diem_nhan", "-id_giao_dich_cong_den"]
        constraints = [
            models.UniqueConstraint(
                fields=["giao_dich_thanh_toan"],
                name=ten_rang_buoc("duy_nhat", BANG_CONG_DEN, "id_giao_dich_thanh_toan"),
            ),
            models.CheckConstraint(
                condition=Q(nguon__in=_ma(NGUON_CONG_DEN)),
                name=ten_rang_buoc("kiem_tra", BANG_CONG_DEN, "nguon_hop_le"),
            ),
            *rang_buoc_van_ban(
                BANG_CONG_DEN, "ma_doi_tac", dinh_dang=MA_THAM_CHIEU, nhan="ma_doi_tac"
            ),
            models.UniqueConstraint(
                fields=["nguon", "ma_doi_tac"],
                name=ten_rang_buoc("duy_nhat", BANG_CONG_DEN, "nguon", "ma_doi_tac"),
            ),
            *rang_buoc_van_ban(
                BANG_CONG_DEN,
                "ma_tham_chieu",
                rong=True,
                dinh_dang=f"^({MA_THAM_CHIEU[1:-1]})?$",
                nhan="tham_chieu",
            ),
            *rang_buoc_van_ban(
                BANG_CONG_DEN,
                "so_tai_khoan_nhan",
                rong=True,
                dinh_dang=r"^[0-9A-Za-z]{0,30}$",
                nhan="tai_khoan",
            ),
            *rang_buoc_so(BANG_CONG_DEN, "so_tien", tien=True),
            *rang_buoc_van_ban(BANG_CONG_DEN, "noi_dung_giao_dich", rong=True, nhan="noi_dung"),
            *rang_buoc_van_ban(BANG_CONG_DEN, "du_lieu_goc", nhieu_dong=True),
            models.CheckConstraint(
                condition=Q(trang_thai__in=_ma(TRANG_THAI_CONG_DEN)),
                name=ten_rang_buoc("kiem_tra", BANG_CONG_DEN, "trang_thai_hop_le"),
            ),
            *rang_buoc_van_ban(BANG_CONG_DEN, "ghi_chu_xu_ly", rong=True, nhan="ghi_chu"),
            # Đã khớp mới có giao dịch; bỏ qua phải ghi lý do.
            models.CheckConstraint(
                condition=Q(trang_thai="da_khop", giao_dich_thanh_toan__isnull=False)
                | (~Q(trang_thai="da_khop") & Q(giao_dich_thanh_toan__isnull=True)),
                name=ten_rang_buoc("kiem_tra", BANG_CONG_DEN, "khop_co_giao_dich"),
            ),
            models.CheckConstraint(
                condition=~Q(trang_thai="bo_qua") | ~Q(ghi_chu_xu_ly=""),
                name=ten_rang_buoc("kiem_tra", BANG_CONG_DEN, "bo_qua_co_ly_do"),
            ),
        ]

    def __str__(self):
        return f"{self.get_nguon_display()} {self.ma_doi_tac}"
