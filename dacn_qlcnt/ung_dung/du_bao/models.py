from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now

from ung_dung.chung.ten_csdl import rang_buoc_van_ban, ten_rang_buoc


class NguonDuLieu(models.Model):
    id_nguon_du_lieu = models.BigAutoField(
        db_column="id_nguon_du_lieu",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ten_nguon_du_lieu = models.TextField(
        db_column="ten_nguon_du_lieu",
        db_comment="Tên nguồn và phiên bản do người nạp nhập; văn bản một dòng.",
    )
    bam_sha256 = models.TextField(
        db_column="bam_sha256",
        db_comment="SHA-256 nội dung nguồn, không phải đường dẫn tệp; văn bản một dòng.",
    )
    don_vi_nguon = models.TextField(
        db_column="don_vi_nguon",
        db_comment="Đơn vị đo theo mô tả nguồn công khai, không đồng nhất kho mô phỏng; văn bản một dòng.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "nguon_du_lieu"
        db_table_comment = "Mỗi hàng là một phiên bản dữ liệu Pharma Sales công khai đã nạp vào DB."
        verbose_name = "Mỗi hàng là một phiên bản dữ liệu Pharma Sales công khai đã nạp vào DB."
        constraints = [
            *rang_buoc_van_ban("nguon_du_lieu", "ten_nguon_du_lieu", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("nguon_du_lieu", "bam_sha256", dinh_dang=r"^[0-9a-f]{64}$"),
            *rang_buoc_van_ban("nguon_du_lieu", "don_vi_nguon", rong=False, nhieu_dong=False),
            models.UniqueConstraint(
                fields=["bam_sha256"],
                name=ten_rang_buoc("duy_nhat", "nguon_du_lieu", *["bam_sha256"]),
            ),
        ]

    def __str__(self):
        return str(self.ten_nguon_du_lieu)


class QuanSatBanHang(models.Model):
    id_quan_sat_ban_hang = models.BigAutoField(
        db_column="id_quan_sat_ban_hang",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    nguon_du_lieu = models.ForeignKey(
        "du_bao.NguonDuLieu",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_nguon_du_lieu",
        db_comment="Phiên bản nguồn.",
    )
    ma_atc_nguon = models.TextField(
        db_column="ma_atc_nguon", db_comment="Mã nhóm ATC của chuỗi công khai; văn bản một dòng."
    )
    ngay_ban = models.DateField(
        db_column="ngay_ban", db_comment="Ngày quan sát trong nguồn 2014–2019."
    )
    so_luong = models.FloatField(
        db_column="so_luong",
        db_comment="Lượng bán công khai; giá trị xấp xỉ, đơn vị theo nguồn công khai.",
    )

    class Meta:
        db_table = "quan_sat_ban_hang"
        db_table_comment = "Mỗi hàng là một quan sát ngày/ATC của dữ liệu công khai, không thuộc chi nhánh mô phỏng."
        verbose_name = "Mỗi hàng là một quan sát ngày/ATC của dữ liệu công khai, không thuộc chi nhánh mô phỏng."
        constraints = [
            *rang_buoc_van_ban("quan_sat_ban_hang", "ma_atc_nguon", rong=False, nhieu_dong=False),
            models.UniqueConstraint(
                fields=["nguon_du_lieu", "ma_atc_nguon", "ngay_ban"],
                name=ten_rang_buoc(
                    "duy_nhat",
                    "quan_sat_ban_hang",
                    *["id_nguon_du_lieu", "ma_atc_nguon", "ngay_ban"],
                ),
            ),
            models.CheckConstraint(
                condition=Q(so_luong__gte=0) & Q(so_luong__lt=float("inf")),
                name="kiem_tra__quan_sat__luong_huu_han_khong_am",
            ),
        ]


class LanThucNghiem(models.Model):
    id_lan_thuc_nghiem = models.BigAutoField(
        db_column="id_lan_thuc_nghiem",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    nguon_du_lieu = models.ForeignKey(
        "du_bao.NguonDuLieu",
        on_delete=models.PROTECT,
        db_column="id_nguon_du_lieu",
        db_comment="Nguồn quan sát độc lập.",
    )
    ngay_chot_huan_luyen = models.DateField(
        db_column="ngay_chot_huan_luyen",
        db_comment="Ngày cuối nhãn tập huấn luyện được phép sử dụng.",
    )
    ngay_chot_xac_thuc = models.DateField(
        db_column="ngay_chot_xac_thuc",
        db_comment="Ngày cuối nhãn tập xác thực, trước tập kiểm thử.",
    )
    ngay_chot_kiem_thu = models.DateField(
        db_column="ngay_chot_kiem_thu", db_comment="Ngày cuối nhãn tập kiểm thử."
    )
    cau_hinh = models.JSONField(
        db_column="cau_hinh",
        db_comment="Cấu hình siêu tham số khác nhau theo mô hình và phiên bản thư viện; không chứa dữ liệu tồn kho.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "lan_thuc_nghiem"
        db_table_comment = "Mỗi hàng là lần thực nghiệm với dữ liệu và các mốc chia theo thời gian."
        verbose_name = "Mỗi hàng là lần thực nghiệm với dữ liệu và các mốc chia theo thời gian."
        constraints = [
            models.CheckConstraint(
                condition=Q(ngay_chot_huan_luyen__lt=F("ngay_chot_xac_thuc"))
                & Q(ngay_chot_xac_thuc__lt=F("ngay_chot_kiem_thu")),
                name="kiem_tra__lan_thuc_nghiem__cac_moc_tang_dan",
            ),
        ]


class KetQuaMoHinh(models.Model):
    id_ket_qua_mo_hinh = models.BigAutoField(
        db_column="id_ket_qua_mo_hinh",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    lan_thuc_nghiem = models.ForeignKey(
        "du_bao.LanThucNghiem",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_lan_thuc_nghiem",
        db_comment="Lần chạy sở hữu kết quả.",
    )
    ma_atc_nguon = models.TextField(
        db_column="ma_atc_nguon", db_comment="Nhóm ATC của kết quả; văn bản một dòng."
    )
    mo_hinh = models.TextField(
        db_column="mo_hinh",
        db_comment="Phương pháp dự báo: hoi_quy_tuyen_tinh, cay_quyet_dinh, rung_ngau_nhien, xgboost hoặc sarimax; văn bản một dòng.",
    )
    mae_xac_thuc = models.FloatField(
        db_column="mae_xac_thuc",
        db_comment="MAE trên tập xác thực do chương trình tính; giá trị xấp xỉ, đơn vị theo nguồn công khai.",
    )
    rmse_xac_thuc = models.FloatField(
        db_column="rmse_xac_thuc",
        db_comment="RMSE trên tập xác thực do chương trình tính; giá trị xấp xỉ, đơn vị theo nguồn công khai.",
    )
    mae_kiem_thu = models.FloatField(
        db_column="mae_kiem_thu",
        db_comment="MAE trên tập kiểm thử do chương trình tính; giá trị xấp xỉ, đơn vị theo nguồn công khai.",
    )
    rmse_kiem_thu = models.FloatField(
        db_column="rmse_kiem_thu",
        db_comment="RMSE trên tập kiểm thử do chương trình tính; giá trị xấp xỉ, đơn vị theo nguồn công khai.",
    )
    duoc_chon = models.BooleanField(
        db_column="duoc_chon",
        db_comment="Mô hình được chọn bằng sai số trên tập xác thực.",
        db_default=False,
    )

    class Meta:
        db_table = "ket_qua_mo_hinh"
        db_table_comment = "Mỗi hàng là sai số của một trong năm mô hình theo nhóm ATC."
        verbose_name = "Mỗi hàng là sai số của một trong năm mô hình theo nhóm ATC."
        constraints = [
            *rang_buoc_van_ban("ket_qua_mo_hinh", "ma_atc_nguon", rong=False, nhieu_dong=False),
            *rang_buoc_van_ban("ket_qua_mo_hinh", "mo_hinh", rong=False, nhieu_dong=False),
            models.UniqueConstraint(
                fields=["lan_thuc_nghiem", "ma_atc_nguon", "mo_hinh"],
                name=ten_rang_buoc(
                    "duy_nhat",
                    "ket_qua_mo_hinh",
                    *["id_lan_thuc_nghiem", "ma_atc_nguon", "mo_hinh"],
                ),
            ),
            models.CheckConstraint(
                condition=Q(
                    mo_hinh__in=[
                        "hoi_quy_tuyen_tinh",
                        "cay_quyet_dinh",
                        "rung_ngau_nhien",
                        "xgboost",
                        "sarimax",
                    ]
                ),
                name="kiem_tra__ket_qua__mo_hinh_hop_le",
            ),
            models.CheckConstraint(
                condition=Q(mae_xac_thuc__gte=0) & Q(mae_xac_thuc__lt=float("inf")),
                name="kiem_tra__ket_qua__mae_xac_thuc_huu_han",
            ),
            models.CheckConstraint(
                condition=Q(rmse_xac_thuc__gte=0) & Q(rmse_xac_thuc__lt=float("inf")),
                name="kiem_tra__ket_qua__rmse_xac_thuc_huu_han",
            ),
            models.CheckConstraint(
                condition=Q(mae_kiem_thu__gte=0) & Q(mae_kiem_thu__lt=float("inf")),
                name="kiem_tra__ket_qua__mae_kiem_thu_huu_han",
            ),
            models.CheckConstraint(
                condition=Q(rmse_kiem_thu__gte=0) & Q(rmse_kiem_thu__lt=float("inf")),
                name="kiem_tra__ket_qua__rmse_kiem_thu_huu_han",
            ),
        ]


class DuBaoBayNgay(models.Model):
    id_du_bao_bay_ngay = models.BigAutoField(
        db_column="id_du_bao_bay_ngay",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    ket_qua_mo_hinh = models.ForeignKey(
        "du_bao.KetQuaMoHinh",
        on_delete=models.PROTECT,
        db_index=False,
        db_column="id_ket_qua_mo_hinh",
        db_comment="Mô hình và phiên bản nguồn đã đánh giá.",
    )
    ngay_goc = models.DateField(
        db_column="ngay_goc", db_comment="Thông tin quan sát chỉ đến hết ngày này."
    )
    ky_danh_gia = models.TextField(
        db_column="ky_danh_gia",
        db_comment="xac_thuc, kiem_thu hoặc tuong_lai; dự báo tổng 7 ngày sau ngày gốc; văn bản một dòng.",
    )
    so_luong_du_bao = models.FloatField(
        db_column="so_luong_du_bao",
        db_comment="Lượng dự báo đã chặn dưới tại 0 trước tính metric; giá trị xấp xỉ, đơn vị theo nguồn công khai.",
    )
    so_luong_thuc_te = models.FloatField(
        db_column="so_luong_thuc_te",
        db_comment="Tổng lượng 7 ngày tương lai để đánh giá; giá trị xấp xỉ, đơn vị theo nguồn công khai. NULL nghĩa là tương lai chưa có thực tế.",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "du_bao_bay_ngay"
        db_table_comment = (
            "Mỗi hàng là tổng lượng dự báo bảy ngày sau một ngày gốc, có đối chiếu khi đã có nhãn."
        )
        verbose_name = (
            "Mỗi hàng là tổng lượng dự báo bảy ngày sau một ngày gốc, có đối chiếu khi đã có nhãn."
        )
        constraints = [
            *rang_buoc_van_ban("du_bao_bay_ngay", "ky_danh_gia", rong=False, nhieu_dong=False),
            models.UniqueConstraint(
                fields=["ket_qua_mo_hinh", "ngay_goc", "ky_danh_gia"],
                name=ten_rang_buoc(
                    "duy_nhat",
                    "du_bao_bay_ngay",
                    *["id_ket_qua_mo_hinh", "ngay_goc", "ky_danh_gia"],
                ),
            ),
            models.CheckConstraint(
                condition=Q(ky_danh_gia__in=["xac_thuc", "kiem_thu", "tuong_lai"]),
                name="kiem_tra__du_bao__ky_hop_le",
            ),
            models.CheckConstraint(
                condition=Q(so_luong_du_bao__gte=0) & Q(so_luong_du_bao__lt=float("inf")),
                name="kiem_tra__du_bao__du_bao_huu_han",
            ),
            models.CheckConstraint(
                condition=Q(so_luong_thuc_te__gte=0) & Q(so_luong_thuc_te__lt=float("inf")),
                name="kiem_tra__du_bao__thuc_te_huu_han",
            ),
            models.CheckConstraint(
                condition=Q(ky_danh_gia="tuong_lai", so_luong_thuc_te__isnull=True)
                | (~Q(ky_danh_gia="tuong_lai") & Q(so_luong_thuc_te__isnull=False)),
                name="kiem_tra__du_bao__thuc_te_dung_ky",
            ),
        ]


class KichBanThieuHang(models.Model):
    id_kich_ban_thieu_hang = models.BigAutoField(
        db_column="id_kich_ban_thieu_hang",
        db_comment="Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.",
        primary_key=True,
    )
    du_bao_bay_ngay = models.ForeignKey(
        "du_bao.DuBaoBayNgay",
        on_delete=models.PROTECT,
        db_column="id_du_bao_bay_ngay",
        db_comment="Dự báo 7 ngày được dùng minh họa.",
    )
    so_luong_ton = models.FloatField(
        db_column="so_luong_ton",
        db_comment="Tồn giả định do người quản lý nhập; giá trị xấp xỉ, đơn vị theo nguồn công khai.",
    )
    so_luong_dang_giu = models.FloatField(
        db_column="so_luong_dang_giu",
        db_comment="Lượng giữ giả định do người quản lý nhập; giá trị xấp xỉ, đơn vị theo nguồn công khai.",
    )
    so_luong_du_tru = models.FloatField(
        db_column="so_luong_du_tru",
        db_comment="Dự trữ giả định do người quản lý nhập; giá trị xấp xỉ, đơn vị theo nguồn công khai.",
    )
    thoi_diem_tao = models.DateTimeField(
        db_column="thoi_diem_tao",
        db_comment="Thời điểm hệ thống ghi nhận nghiệp vụ.",
        db_default=Now(),
    )

    class Meta:
        db_table = "kich_ban_thieu_hang"
        db_table_comment = "Mỗi hàng là kịch bản minh họa riêng theo đơn vị dữ liệu công khai; không tác động kho mô phỏng."
        verbose_name = "Mỗi hàng là kịch bản minh họa riêng theo đơn vị dữ liệu công khai"
        constraints = [
            models.CheckConstraint(
                condition=Q(so_luong_ton__gte=0) & Q(so_luong_ton__lt=float("inf")),
                name="kiem_tra__kich_ban_thieu_hang__so_luong_ton_khong_am",
            ),
            models.CheckConstraint(
                condition=Q(so_luong_dang_giu__gte=0) & Q(so_luong_dang_giu__lt=float("inf")),
                name="kiem_tra__kich_ban_thieu_hang__so_luong_dang_giu_khong_am",
            ),
            models.CheckConstraint(
                condition=Q(so_luong_du_tru__gte=0) & Q(so_luong_du_tru__lt=float("inf")),
                name="kiem_tra__kich_ban_thieu_hang__so_luong_du_tru_khong_am",
            ),
            models.CheckConstraint(
                condition=Q(so_luong_dang_giu__lte=F("so_luong_ton")),
                name="kiem_tra__kich_ban_thieu_hang__giu_khong_vuot_ton",
            ),
        ]
