from django.db import models
from django.db.models import Q
from django.db.models.functions import Length, Now
from django.db.models.lookups import LessThanOrEqual

from ung_dung.chung.ten_csdl import MA_UUID, rang_buoc_van_ban, ten_rang_buoc

LOAI_CUOC_TRO_CHUYEN = [
    ("tu_van", "Tư vấn"),
    ("don_hang", "Về đơn hàng"),
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
        db_comment="Khách sở hữu phòng.",
    )
    chi_nhanh = models.ForeignKey(
        "danh_muc.ChiNhanh",
        on_delete=models.PROTECT,
        db_column="id_chi_nhanh",
        db_comment="Chi nhánh phụ trách trao đổi; với phòng về đơn hàng là chi nhánh của đơn.",
    )
    loai_cuoc_tro_chuyen = models.TextField(
        choices=LOAI_CUOC_TRO_CHUYEN,
        default="tu_van",
        db_default="tu_van",
        db_column="loai_cuoc_tro_chuyen",
        db_comment=(
            "tu_van: khách hỏi thuốc, mỗi khách một phòng với mỗi chi nhánh; "
            "don_hang: trao đổi về đúng một đơn hàng."
        ),
    )
    don_hang = models.ForeignKey(
        "ban_hang.DonHang",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cac_cuoc_tro_chuyen",
        db_column="id_don_hang",
        db_comment=(
            "Đơn được trao đổi; NULL với phòng tư vấn. Service kiểm đơn thuộc đúng khách "
            "và chi nhánh của phòng."
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
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "cuoc_tro_chuyen"
        db_table_comment = (
            "Mỗi hàng là phòng trò chuyện của một khách với một chi nhánh: phòng tư vấn chung "
            "hoặc phòng về một đơn hàng."
        )
        verbose_name = (
            "Mỗi hàng là phòng trò chuyện của một khách với một chi nhánh: phòng tư vấn chung "
            "hoặc phòng về một đơn hàng."
        )
        constraints = [
            *rang_buoc_van_ban(
                "cuoc_tro_chuyen", "loai_cuoc_tro_chuyen", rong=False, nhieu_dong=False
            ),
            models.CheckConstraint(
                condition=Q(loai_cuoc_tro_chuyen__in=[ma for ma, _ in LOAI_CUOC_TRO_CHUYEN]),
                name=ten_rang_buoc("kiem_tra", "cuoc_tro_chuyen", "loai_hop_le"),
            ),
            # NULLS NOT DISTINCT: phòng tư vấn (đơn NULL) chỉ có một cho mỗi khách và chi nhánh.
            models.UniqueConstraint(
                fields=["khach_hang", "chi_nhanh", "don_hang"],
                nulls_distinct=False,
                name=ten_rang_buoc(
                    "duy_nhat",
                    "cuoc_tro_chuyen",
                    *["id_tai_khoan_khach", "id_chi_nhanh", "id_don_hang"],
                ),
            ),
            models.UniqueConstraint(
                fields=["don_hang"],
                name=ten_rang_buoc("duy_nhat", "cuoc_tro_chuyen", "id_don_hang"),
            ),
            models.CheckConstraint(
                condition=Q(loai_cuoc_tro_chuyen="tu_van", don_hang__isnull=True)
                | Q(loai_cuoc_tro_chuyen="don_hang", don_hang__isnull=False),
                name=ten_rang_buoc("kiem_tra", "cuoc_tro_chuyen", "loai_khop_don_hang"),
                violation_error_message="Phòng về đơn hàng phải gắn đơn; phòng tư vấn thì không.",
            ),
        ]

    @property
    def la_don_hang(self):
        return self.loai_cuoc_tro_chuyen == "don_hang"


class TinNhan(models.Model):
    id_tin_nhan = models.BigAutoField(
        db_column="id_tin_nhan",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    cuoc_tro_chuyen = models.ForeignKey(
        "tro_chuyen.CuocTroChuyen",
        on_delete=models.PROTECT,
        db_column="id_cuoc_tro_chuyen",
        db_comment="Phòng sở hữu tin.",
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
        db_column="noi_dung_tin_nhan",
        db_comment="Nội dung khách/nhân viên nhập; cho phép nhiều dòng.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "tin_nhan"
        db_table_comment = "Mỗi hàng là tin đã được ghi bền vững trước khi phát Redis."
        verbose_name = "Mỗi hàng là tin đã được ghi bền vững trước khi phát Redis."
        constraints = [
            *rang_buoc_van_ban("tin_nhan", "ma_tin_nhan", dinh_dang=MA_UUID),
            *rang_buoc_van_ban("tin_nhan", "noi_dung_tin_nhan", rong=False, nhieu_dong=True),
            models.UniqueConstraint(
                fields=["nguoi_gui", "ma_tin_nhan"],
                name=ten_rang_buoc("duy_nhat", "tin_nhan", *["id_tai_khoan_gui", "ma_tin_nhan"]),
            ),
            models.CheckConstraint(
                condition=LessThanOrEqual(Length("noi_dung_tin_nhan"), 2000),
                name="kiem_tra__tin_nhan__noi_dung_toi_da_2000_ky_tu",
            ),
        ]
