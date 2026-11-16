# Bản nộp theo đề cương (Q45): đơn chỉ còn đặt giữ nhận tại quầy; bỏ giao hàng, thanh toán trực
# tuyến, trả hàng và hoàn kho; phiếu bán ghi cách khách trả tiền tại quầy.

import django.db.models.deletion
import django.db.models.expressions
from django.conf import settings
from django.db import migrations, models


def chep_cach_tra_va_bo_bang_thanh_toan(apps, schema_editor):
    """CSDL cũ (đã qua kiểm tra ở 0017) có thể còn bảng của app thanh_toan đã gỡ: chép cách trả
    tại quầy sang phiếu bán rồi xóa các bảng đó. CSDL mới không có bảng nên bỏ qua."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.giao_dich_thanh_toan') IS NOT NULL")
        if not cursor.fetchone()[0]:
            return
        cursor.execute(
            "UPDATE phieu_ban p SET phuong_thuc_thanh_toan = g.phuong_thuc "
            "FROM giao_dich_thanh_toan g WHERE g.id_phieu_ban = p.id_phieu_ban "
            "AND g.loai_giao_dich = 'thu'"
        )
        cursor.execute("DROP TABLE IF EXISTS giao_dich_cong_den, giao_dich_thanh_toan")
        cursor.execute("DELETE FROM django_migrations WHERE app = 'thanh_toan'")


class Migration(migrations.Migration):
    dependencies = [
        ("ban_hang", "0017_kiem_tra_csdl_ban_nop"),
        ("danh_muc", "0017_ghi_chu_thuoc_ke_don_ban_tai_quay"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="anhtrahang",
            name="chi_muc__anh_tra_hang__id_yeu_cau_tra_hang__thu_tu",
        ),
        migrations.RemoveConstraint(
            model_name="anhtrahang",
            name="kiem_tra__anh_tra_hang__bam_sha256_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="anhtrahang",
            name="kiem_tra__anh_tra_hang__bam_sha256_khong_rong",
        ),
        migrations.RemoveConstraint(
            model_name="anhtrahang",
            name="kiem_tra__anh_tra_hang__bam_sha256_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="anhtrahang",
            name="kiem_tra__anh_tra_hang__bam_sha256_dung_dinh_dang",
        ),
        migrations.RemoveConstraint(
            model_name="anhtrahang",
            name="kiem_tra__anh_tra_hang__kich_thuoc_byte_khop",
        ),
        migrations.RemoveConstraint(
            model_name="anhtrahang",
            name="kiem_tra__anh_tra_hang__kich_thuoc_anh_hop_le",
        ),
        migrations.RemoveConstraint(
            model_name="anhtrahang",
            name="kiem_tra__anh_tra_hang__thu_tu_khong_am",
        ),
        migrations.RemoveConstraint(
            model_name="chitietphieuhoankho",
            name="kiem_tra__ct_hoan_kho__so_luong_duong",
        ),
        migrations.RemoveConstraint(
            model_name="chitietphieuhoankho",
            name="duy_nhat__ct_hoan_kho__id_phan_bo_phieu_ban",
        ),
        migrations.RemoveConstraint(
            model_name="chitiettrahang",
            name="duy_nhat__ct_tra__id_yeu_cau_tra_hang__id_chi_tiet_don_hang",
        ),
        migrations.RemoveConstraint(
            model_name="chitiettrahang",
            name="kiem_tra__ct_tra__so_luong_duong",
        ),
        migrations.RemoveConstraint(
            model_name="chitiettrahang",
            name="kiem_tra__ct_tra__nhap_lai_khong_vuot_so_tra",
        ),
        migrations.RemoveConstraint(
            model_name="hangtrachohuy",
            name="kiem_tra__hang_huy__so_luong_duong",
        ),
        migrations.RemoveConstraint(
            model_name="hangtrachohuy",
            name="duy_nhat__hang_huy__id_chi_tiet_tra_hang__id_phan_bo_phieu_ban",
        ),
        migrations.RemoveConstraint(
            model_name="hangtrachohuy",
            name="kiem_tra__hang_huy__trang_thai_hop_le",
        ),
        migrations.RemoveConstraint(
            model_name="hangtrachohuy",
            name="kiem_tra__hang_huy__phieu_huy_dung_trang_thai",
        ),
        migrations.RemoveConstraint(
            model_name="phanbotrahang",
            name="kiem_tra__pb_tra__so_luong_duong",
        ),
        migrations.RemoveConstraint(
            model_name="phanbotrahang",
            name="duy_nhat__pb_tra__id_chi_tiet_tra_hang__id_phan_bo_phieu_ban",
        ),
        migrations.RemoveConstraint(
            model_name="phieuhoankho",
            name="kiem_tra__phieu_hoan_kho__ma_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="phieuhoankho",
            name="kiem_tra__phieu_hoan_kho__ma_khong_rong",
        ),
        migrations.RemoveConstraint(
            model_name="phieuhoankho",
            name="kiem_tra__phieu_hoan_kho__ma_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="phieuhoankho",
            name="kiem_tra__phieu_hoan_kho__ma_dung_dinh_dang",
        ),
        migrations.RemoveConstraint(
            model_name="phieuhoankho",
            name="duy_nhat__phieu_hoan_kho__ma_phieu_hoan_kho",
        ),
        migrations.RemoveConstraint(
            model_name="phieuhoankho",
            name="duy_nhat__phieu_hoan_kho__id_phieu_ban",
        ),
        migrations.RemoveConstraint(
            model_name="phieuhoankho",
            name="kiem_tra__phieu_hoan_kho__ly_do_hop_le",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__ma_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__ma_khong_rong",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__ma_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__ma_dung_dinh_dang",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="duy_nhat__tra_hang__ma_yeu_cau_tra_hang",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__ly_do_hop_le",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__trang_thai_hop_le",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__mo_ta_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__mo_ta_khong_rong",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__ghi_chu_xu_ly_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__so_tien_hoan_khong_am",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__so_tien_hoan_khong_phai_nan",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__xu_ly_dung_trang_thai",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__tu_choi_co_ly_do",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__hinh_thuc_hoan_hop_le",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__ten_ngan_hang_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__ten_ngan_hang_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__so_tai_khoan_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__so_tai_khoan_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__so_tai_khoan_dung_dinh_dang",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__ten_chu_tai_khoan_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__ten_chu_tai_khoan_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__ten_chu_tai_khoan_dung_dinh_dang",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__so_dien_thoai_momo_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__so_dien_thoai_momo_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__thong_tin_hoan_dung_cach",
        ),
        migrations.RemoveConstraint(
            model_name="yeucautrahang",
            name="kiem_tra__tra_hang__so_dien_thoai_momo_dung_dinh_dang",
        ),
        migrations.AlterModelOptions(
            name="donhang",
            options={"ordering": ["-id_don_hang"], "verbose_name": "đơn đặt giữ"},
        ),
        migrations.AlterModelTableComment(
            name="donhang",
            table_comment="Mỗi hàng là một đơn đặt giữ của khách ở một chi nhánh; khách nhận và trả tiền tại quầy.",
        ),
        migrations.AlterModelTableComment(
            name="phieuban",
            table_comment="Mỗi hàng là một lần bán tại quầy kèm xuất kho: bán trực tiếp hoặc giao đơn đặt giữ cho khách đến nhận.",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__trang_thai_hop_le",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__hinh_thuc_nhan_hop_le",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__phuong_thuc_hop_le",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__trang_thai_thanh_toan_hop_le",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__du_lieu_dung_hinh_thuc_nhan",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__phi_giao_hang_khong_am",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__phi_giao_hang_khong_phai_nan",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__tong_dung_cong_thuc",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__ten_nguoi_nhan_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__ten_nguoi_nhan_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__so_dien_thoai_nhan_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__so_dien_thoai_nhan_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__dia_chi_giao_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__dia_chi_giao_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__so_dien_thoai_nhan_dung_dinh_dang",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__cod_khong_cho_thanh_toan",
        ),
        migrations.RemoveConstraint(
            model_name="donhang",
            name="kiem_tra__don_hang__cho_thanh_toan_thi_chua_thu",
        ),
        migrations.RemoveConstraint(
            model_name="lichsudonhang",
            name="kiem_tra__lich_su_don_hang__tu_trang_thai_hop_le",
        ),
        migrations.RemoveConstraint(
            model_name="lichsudonhang",
            name="kiem_tra__lich_su_don_hang__den_trang_thai_hop_le",
        ),
        migrations.AddField(
            model_name="phieuban",
            name="phuong_thuc_thanh_toan",
            field=models.TextField(
                choices=[("tien_mat", "Tiền mặt"), ("chuyen_khoan", "Chuyển khoản")],
                db_column="phuong_thuc_thanh_toan",
                db_comment="Cách khách trả tiền tại quầy: tien_mat hoặc chuyen_khoan; nhân viên lập phiếu xác nhận đã nhận đủ tiền.",
                db_default="tien_mat",
                default="tien_mat",
            ),
        ),
        migrations.RunPython(chep_cach_tra_va_bo_bang_thanh_toan, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="donhang",
            name="chi_nhanh",
            field=models.ForeignKey(
                db_column="id_chi_nhanh",
                db_comment="Chi nhánh duy nhất giữ hàng, nơi khách đến nhận và trả tiền.",
                on_delete=django.db.models.deletion.PROTECT,
                to="danh_muc.chinhanh",
            ),
        ),
        migrations.AlterField(
            model_name="donhang",
            name="ghi_chu_khach",
            field=models.TextField(
                blank=True,
                db_column="ghi_chu_khach",
                db_comment="Lời nhắn của khách cho nhà thuốc; một dòng, có thể rỗng.",
                db_default="",
            ),
        ),
        migrations.AlterField(
            model_name="donhang",
            name="thoi_diem_het_giu",
            field=models.DateTimeField(
                db_column="thoi_diem_het_giu",
                db_comment="Hạn của lượng giữ hàng, 24 giờ sau khi đặt; quá hạn thì đơn hết hạn.",
            ),
        ),
        migrations.AlterField(
            model_name="donhang",
            name="tong_thanh_toan",
            field=models.DecimalField(
                db_column="tong_thanh_toan",
                db_comment="Số tiền khách trả tại quầy, bằng tiền hàng trừ giảm giá thành viên; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.",
                db_default=0,
                decimal_places=0,
                default=0,
                max_digits=14,
            ),
        ),
        migrations.AlterField(
            model_name="donhang",
            name="trang_thai",
            field=models.TextField(
                choices=[
                    ("dang_giu", "Đang giữ hàng"),
                    ("hoan_thanh", "Đã nhận hàng"),
                    ("da_huy", "Đã hủy"),
                    ("het_han", "Hết hạn giữ"),
                ],
                db_column="trang_thai",
                db_comment="Trạng thái xử lý; chỉ service đổi theo bảng chuyển hợp lệ và ghi lich_su_don_hang: dang_giu, hoan_thanh (khách đã nhận và trả tiền tại quầy), da_huy, het_han.",
                db_default="dang_giu",
                default="dang_giu",
            ),
        ),
        migrations.AlterField(
            model_name="lichsudonhang",
            name="den_trang_thai",
            field=models.TextField(
                choices=[
                    ("dang_giu", "Đang giữ hàng"),
                    ("hoan_thanh", "Đã nhận hàng"),
                    ("da_huy", "Đã hủy"),
                    ("het_han", "Hết hạn giữ"),
                ],
                db_column="den_trang_thai",
                db_comment="Trạng thái sau khi đổi.",
            ),
        ),
        migrations.AlterField(
            model_name="lichsudonhang",
            name="tu_trang_thai",
            field=models.TextField(
                blank=True,
                choices=[
                    ("dang_giu", "Đang giữ hàng"),
                    ("hoan_thanh", "Đã nhận hàng"),
                    ("da_huy", "Đã hủy"),
                    ("het_han", "Hết hạn giữ"),
                ],
                db_column="tu_trang_thai",
                db_comment="Trạng thái trước khi đổi; NULL ở dòng tạo đơn.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="phieuban",
            name="don_hang",
            field=models.ForeignKey(
                blank=True,
                db_column="id_don_hang",
                db_comment="Đơn đặt giữ khách đến nhận; NULL nghĩa là bán trực tiếp tại quầy.",
                db_index=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="ban_hang.donhang",
            ),
        ),
        migrations.AddConstraint(
            model_name="donhang",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("trang_thai__in", ["dang_giu", "hoan_thanh", "da_huy", "het_han"])
                ),
                name="kiem_tra__don_hang__trang_thai_hop_le",
            ),
        ),
        migrations.AddConstraint(
            model_name="donhang",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "tong_thanh_toan",
                        django.db.models.expressions.CombinedExpression(
                            models.F("tien_hang"), "-", models.F("giam_gia_thanh_vien")
                        ),
                    ),
                    ("giam_gia_thanh_vien__lte", models.F("tien_hang")),
                ),
                name="kiem_tra__don_hang__tong_dung_cong_thuc",
            ),
        ),
        migrations.AddConstraint(
            model_name="lichsudonhang",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("tu_trang_thai__isnull", True),
                    (
                        "tu_trang_thai__in",
                        ["dang_giu", "hoan_thanh", "da_huy", "het_han"],
                    ),
                    _connector="OR",
                ),
                name="kiem_tra__lich_su_don_hang__tu_trang_thai_hop_le",
            ),
        ),
        migrations.AddConstraint(
            model_name="lichsudonhang",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "den_trang_thai__in",
                        ["dang_giu", "hoan_thanh", "da_huy", "het_han"],
                    )
                ),
                name="kiem_tra__lich_su_don_hang__den_trang_thai_hop_le",
            ),
        ),
        migrations.AddConstraint(
            model_name="phieuban",
            constraint=models.CheckConstraint(
                condition=models.Q(("phuong_thuc_thanh_toan__in", ["tien_mat", "chuyen_khoan"])),
                name="kiem_tra__phieu_ban__phuong_thuc_thanh_toan_hop_le",
            ),
        ),
        migrations.RemoveField(
            model_name="chitietphieuhoankho",
            name="phan_bo_phieu_ban",
        ),
        migrations.RemoveField(
            model_name="chitietphieuhoankho",
            name="phieu_hoan_kho",
        ),
        migrations.RemoveField(
            model_name="chitiettrahang",
            name="chi_tiet_don_hang",
        ),
        migrations.RemoveField(
            model_name="chitiettrahang",
            name="yeu_cau_tra_hang",
        ),
        migrations.RemoveField(
            model_name="hangtrachohuy",
            name="chi_tiet_tra_hang",
        ),
        migrations.RemoveField(
            model_name="hangtrachohuy",
            name="phan_bo_phieu_ban",
        ),
        migrations.RemoveField(
            model_name="hangtrachohuy",
            name="phieu_xuat_huy",
        ),
        migrations.RemoveField(
            model_name="phanbotrahang",
            name="chi_tiet_tra_hang",
        ),
        migrations.RemoveField(
            model_name="phanbotrahang",
            name="phan_bo_phieu_ban",
        ),
        migrations.RemoveField(
            model_name="phieuhoankho",
            name="nguoi_lap",
        ),
        migrations.RemoveField(
            model_name="phieuhoankho",
            name="phieu_ban",
        ),
        migrations.RemoveField(
            model_name="yeucautrahang",
            name="don_hang",
        ),
        migrations.RemoveField(
            model_name="yeucautrahang",
            name="nguoi_xu_ly",
        ),
        migrations.RemoveField(
            model_name="donhang",
            name="dia_chi_giao",
        ),
        migrations.RemoveField(
            model_name="donhang",
            name="hinh_thuc_nhan",
        ),
        migrations.RemoveField(
            model_name="donhang",
            name="khoang_cach_met",
        ),
        migrations.RemoveField(
            model_name="donhang",
            name="phi_giao_hang",
        ),
        migrations.RemoveField(
            model_name="donhang",
            name="phuong_thuc_thanh_toan",
        ),
        migrations.RemoveField(
            model_name="donhang",
            name="so_dien_thoai_nhan",
        ),
        migrations.RemoveField(
            model_name="donhang",
            name="ten_nguoi_nhan",
        ),
        migrations.RemoveField(
            model_name="donhang",
            name="trang_thai_thanh_toan",
        ),
        migrations.RemoveField(
            model_name="donhang",
            name="vi_tri_giao",
        ),
        migrations.DeleteModel(
            name="AnhTraHang",
        ),
        migrations.DeleteModel(
            name="ChiTietPhieuHoanKho",
        ),
        migrations.DeleteModel(
            name="HangTraChoHuy",
        ),
        migrations.DeleteModel(
            name="ChiTietTraHang",
        ),
        migrations.DeleteModel(
            name="PhanBoTraHang",
        ),
        migrations.DeleteModel(
            name="PhieuHoanKho",
        ),
        migrations.DeleteModel(
            name="YeuCauTraHang",
        ),
    ]
