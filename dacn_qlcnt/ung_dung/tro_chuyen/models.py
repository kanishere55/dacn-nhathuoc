from django.db import models
from django.db.models import Q
from django.db.models.functions import Length, Now
from django.db.models.lookups import LessThanOrEqual

from ung_dung.chung.anh import AnhCSDL, rang_buoc_anh
from ung_dung.chung.ten_csdl import MA_UUID, rang_buoc_van_ban, ten_rang_buoc

# Một tin kèm tối đa từng này ảnh (thu_tu 0..4, duy nhất trong tin).
SO_ANH_TOI_DA = 5

TRANG_THAI_XU_LY = [
    ("dang_mo", "Đang trao đổi"),
    ("da_xong", "Đã xong"),
]


class CuocTroChuyen(models.Model):
    id_cuoc_tro_chuyen = models.BigAutoField(
        db_column="id_cuoc_tro_chuyen",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    khach_hang = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_tai_khoan_khach",
        db_comment="Khách sở hữu cuộc trò chuyện.",
    )
    chi_nhanh = models.ForeignKey(
        "danh_muc.ChiNhanh",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_chi_nhanh",
        db_comment=(
            "Chi nhánh trả lời. Mọi câu hỏi của khách với chi nhánh (tư vấn, sản phẩm, đơn hàng) "
            "nằm chung một cuộc trò chuyện; thẻ sản phẩm/đơn gắn ở từng tin."
        ),
    )
    tin_khach_da_doc = models.ForeignKey(
        "tro_chuyen.TinNhan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="id_tin_nhan_khach_da_doc",
        db_comment=(
            "Tin mới nhất khách đã xem; tin của nhà thuốc có id lớn hơn là chưa đọc. "
            "NULL khi khách chưa mở phòng. Service chỉ cho tăng và chỉ trỏ tin trong phòng."
        ),
    )
    tin_nha_thuoc_da_doc = models.ForeignKey(
        "tro_chuyen.TinNhan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="id_tin_nhan_nha_thuoc_da_doc",
        db_comment=(
            "Tin mới nhất phía nhà thuốc đã xem (bất kỳ nhân sự nào của chi nhánh mở phòng); "
            "tin của khách có id lớn hơn là chưa đọc."
        ),
    )
    tin_cuoi = models.ForeignKey(
        "tro_chuyen.TinNhan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="id_tin_nhan_cuoi",
        db_comment=(
            "Tin mới nhất của phòng, service cập nhật trong cùng giao dịch ghi tin. Lưu sẵn để "
            "hộp thư hàng nghìn phòng sắp xếp, lọc Chờ trả lời bằng chỉ mục thay vì quét tin_nhan. "
            "Phòng chỉ được tạo cùng tin đầu tiên nên NULL chỉ còn ở dữ liệu cũ."
        ),
    )
    trang_thai_xu_ly = models.TextField(
        choices=TRANG_THAI_XU_LY,
        default="dang_mo",
        db_default="dang_mo",
        db_column="trang_thai_xu_ly",
        db_comment=(
            "dang_mo: còn cần theo dõi; da_xong: nhân sự đánh dấu đã giải quyết. "
            "Khách gửi tin mới thì phòng tự mở lại."
        ),
    )
    thoi_diem_xong = models.DateTimeField(
        null=True,
        blank=True,
        db_column="thoi_diem_xong",
        db_comment="Lúc đánh dấu đã xong; NULL khi đang trao đổi.",
    )
    nguoi_danh_dau_xong = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="id_tai_khoan_danh_dau_xong",
        db_comment="Nhân sự đánh dấu đã xong; NULL khi đang trao đổi.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "cuoc_tro_chuyen"
        db_table_comment = (
            "Mỗi hàng là cuộc trò chuyện duy nhất của một khách với một chi nhánh, giữ toàn bộ "
            "lịch sử hỏi tư vấn, sản phẩm và đơn hàng."
        )
        verbose_name = "cuộc trò chuyện"
        indexes = [
            # Hộp thư nhân sự: phòng của chi nhánh, mới nhất trước.
            models.Index(
                fields=["chi_nhanh", "-tin_cuoi"],
                name=ten_rang_buoc(
                    "chi_muc", "cuoc_tro_chuyen", "id_chi_nhanh", "id_tin_nhan_cuoi"
                ),
            ),
            # Hộp thư khách.
            models.Index(
                fields=["khach_hang", "-tin_cuoi"],
                name=ten_rang_buoc(
                    "chi_muc", "cuoc_tro_chuyen", "id_tai_khoan_khach", "id_tin_nhan_cuoi"
                ),
            ),
        ]
        constraints = [
            *rang_buoc_van_ban("cuoc_tro_chuyen", "trang_thai_xu_ly", rong=False, nhieu_dong=False),
            models.CheckConstraint(
                condition=Q(trang_thai_xu_ly__in=[ma for ma, _ in TRANG_THAI_XU_LY]),
                name=ten_rang_buoc("kiem_tra", "cuoc_tro_chuyen", "trang_thai_hop_le"),
            ),
            models.CheckConstraint(
                condition=Q(
                    trang_thai_xu_ly="dang_mo",
                    thoi_diem_xong__isnull=True,
                    nguoi_danh_dau_xong__isnull=True,
                )
                | Q(
                    trang_thai_xu_ly="da_xong",
                    thoi_diem_xong__isnull=False,
                    nguoi_danh_dau_xong__isnull=False,
                ),
                name=ten_rang_buoc("kiem_tra", "cuoc_tro_chuyen", "trang_thai_khop_moc_xong"),
                violation_error_message="Phòng đã xong phải có thời điểm và người đánh dấu.",
            ),
            models.UniqueConstraint(
                fields=["khach_hang", "chi_nhanh"],
                name=ten_rang_buoc(
                    "duy_nhat", "cuoc_tro_chuyen", "id_tai_khoan_khach", "id_chi_nhanh"
                ),
            ),
        ]

    @property
    def da_xong(self):
        return self.trang_thai_xu_ly == "da_xong"


class TinNhan(models.Model):
    id_tin_nhan = models.BigAutoField(
        db_column="id_tin_nhan",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    cuoc_tro_chuyen = models.ForeignKey(
        "tro_chuyen.CuocTroChuyen",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_cuoc_tro_chuyen",
        db_comment="Cuộc trò chuyện sở hữu tin.",
    )
    nguoi_gui = models.ForeignKey(
        "tai_khoan.TaiKhoan",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_tai_khoan_gui",
        db_comment="Người gửi được xác định từ phiên đăng nhập.",
    )
    ma_tin_nhan = models.TextField(
        db_column="ma_tin_nhan",
        db_comment="UUID chống gửi trùng do trình duyệt tạo; văn bản một dòng.",
    )
    noi_dung_tin_nhan = models.TextField(
        blank=True,
        default="",
        db_default="",
        db_column="noi_dung_tin_nhan",
        db_comment=(
            "Nội dung khách/nhân viên nhập; cho phép nhiều dòng. Rỗng khi tin chỉ gồm ảnh "
            "(so_anh > 0)."
        ),
    )
    so_anh = models.SmallIntegerField(
        default=0,
        db_default=0,
        db_column="so_anh",
        db_comment=(
            "Số ảnh đính kèm trong anh_tin_nhan, 0 đến 5; service ghi cùng giao dịch với ảnh. "
            "Lưu sẵn để ràng buộc tin phải có chữ hoặc ảnh và để hộp thư hiện 'Đã gửi ảnh'."
        ),
    )
    thuoc = models.ForeignKey(
        "danh_muc.Thuoc",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        db_index=False,
        db_column="id_thuoc",
        db_comment=(
            "Thẻ sản phẩm 'Bạn đang hỏi về sản phẩm này' khi khách bắt đầu hỏi từ trang thuốc; "
            "NULL với tin thường."
        ),
    )
    don_hang = models.ForeignKey(
        "ban_hang.DonHang",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cac_tin_nhan",
        db_index=False,
        db_column="id_don_hang",
        db_comment=(
            "Thẻ đơn hàng khi tin hỏi về một đơn; service kiểm đơn thuộc đúng khách và chi "
            "nhánh của cuộc trò chuyện. NULL với tin thường."
        ),
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "tin_nhan"
        db_table_comment = "Mỗi hàng là tin đã được ghi bền vững trước khi phát Redis."
        verbose_name = "tin nhắn"
        indexes = [
            # Lịch sử tải dần (tin cũ hơn một mốc) và đếm tin chưa đọc sau mốc đã đọc.
            models.Index(
                fields=["cuoc_tro_chuyen", "-id_tin_nhan"],
                name=ten_rang_buoc("chi_muc", "tin_nhan", "id_cuoc_tro_chuyen", "id_tin_nhan"),
            ),
            # Chỉ mục khóa ngoại: tìm tin đã hỏi về một đơn / thuốc và kiểm PROTECT khi xóa.
            models.Index(
                fields=["don_hang"],
                name=ten_rang_buoc("chi_muc", "tin_nhan", "id_don_hang"),
            ),
            models.Index(
                fields=["thuoc"],
                name=ten_rang_buoc("chi_muc", "tin_nhan", "id_thuoc"),
            ),
        ]
        constraints = [
            *rang_buoc_van_ban("tin_nhan", "ma_tin_nhan", dinh_dang=MA_UUID),
            *rang_buoc_van_ban("tin_nhan", "noi_dung_tin_nhan", rong=True, nhieu_dong=True),
            models.CheckConstraint(
                condition=Q(so_anh__gte=0, so_anh__lte=SO_ANH_TOI_DA),
                name=ten_rang_buoc("kiem_tra", "tin_nhan", "so_anh_hop_le"),
            ),
            models.CheckConstraint(
                condition=~Q(noi_dung_tin_nhan="") | Q(so_anh__gt=0),
                name=ten_rang_buoc("kiem_tra", "tin_nhan", "co_chu_hoac_anh"),
                violation_error_message="Tin nhắn phải có nội dung hoặc ít nhất một ảnh.",
            ),
            models.CheckConstraint(
                condition=Q(thuoc__isnull=True) | Q(don_hang__isnull=True),
                name=ten_rang_buoc("kiem_tra", "tin_nhan", "toi_da_mot_the"),
                violation_error_message="Một tin chỉ gắn thẻ sản phẩm hoặc thẻ đơn hàng.",
            ),
            models.UniqueConstraint(
                fields=["nguoi_gui", "ma_tin_nhan"],
                name=ten_rang_buoc("duy_nhat", "tin_nhan", *["id_tai_khoan_gui", "ma_tin_nhan"]),
            ),
            models.CheckConstraint(
                condition=LessThanOrEqual(Length("noi_dung_tin_nhan"), 2000),
                name="kiem_tra__tin_nhan__noi_dung_toi_da_2000_ky_tu",
            ),
        ]


class AnhTinNhan(AnhCSDL):
    id_anh_tin_nhan = models.BigAutoField(
        primary_key=True,
        db_column="id_anh_tin_nhan",
        db_comment="Định danh nội bộ PostgreSQL cấp, dùng trên đường dẫn ảnh riêng tư.",
    )
    tin_nhan = models.ForeignKey(
        "tro_chuyen.TinNhan",
        on_delete=models.PROTECT,
        related_name="cac_anh",
        db_index=False,
        db_column="id_tin_nhan",
        db_comment="Tin sở hữu ảnh; chỉ khách và nhân sự phụ trách cuộc trò chuyện xem được.",
    )

    class Meta:
        db_table = "anh_tin_nhan"
        db_table_comment = "Mỗi hàng là một ảnh gửi kèm tin nhắn trò chuyện, lưu bytea."
        verbose_name = "ảnh tin nhắn"
        ordering = ["thu_tu", "id_anh_tin_nhan"]
        constraints = [
            *rang_buoc_anh("anh_tin_nhan"),
            models.CheckConstraint(
                condition=Q(thu_tu__lt=SO_ANH_TOI_DA),
                name=ten_rang_buoc("kiem_tra", "anh_tin_nhan", "thu_tu_toi_da"),
            ),
            # Chỉ mục duy nhất này cũng phục vụ việc lấy ảnh theo tin.
            models.UniqueConstraint(
                fields=["tin_nhan", "thu_tu"],
                name=ten_rang_buoc("duy_nhat", "anh_tin_nhan", "id_tin_nhan", "thu_tu"),
            ),
        ]
