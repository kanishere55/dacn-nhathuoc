# Bản nộp theo đề cương (Q45): bỏ sổ địa chỉ giao hàng và các quyền của giao hàng, thanh toán
# trực tuyến, trả hàng, hoàn tiền.

from django.db import migrations

QUYEN_DA_BO = ("don_hang.hoan_tien", "thanh_toan.xac_nhan", "tra_hang.xem", "tra_hang.duyet")


def bo_quyen(apps, schema_editor):
    for ten in ("QuyenCuaNhom", "QuyenRiengTaiKhoan"):
        apps.get_model("tai_khoan", ten).objects.using(schema_editor.connection.alias).filter(
            ma_quyen__in=QUYEN_DA_BO
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ban_hang", "0017_kiem_tra_csdl_ban_nop"),
        ("tai_khoan", "0014_bo_sung_quyen_mac_dinh_quan_ly"),
    ]

    operations = [
        migrations.RunPython(bo_quyen, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="diachigiaohang",
            name="kiem_tra__dia_chi_giao_hang__ten_nguoi_nhan_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="diachigiaohang",
            name="kiem_tra__dia_chi_giao_hang__ten_nguoi_nhan_khong_rong",
        ),
        migrations.RemoveConstraint(
            model_name="diachigiaohang",
            name="kiem_tra__dia_chi_giao_hang__ten_nguoi_nhan_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="diachigiaohang",
            name="kiem_tra__dia_chi_giao_hang__so_dien_thoai_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="diachigiaohang",
            name="kiem_tra__dia_chi_giao_hang__so_dien_thoai_khong_rong",
        ),
        migrations.RemoveConstraint(
            model_name="diachigiaohang",
            name="kiem_tra__dia_chi_giao_hang__so_dien_thoai_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="diachigiaohang",
            name="kiem_tra__dia_chi_giao_hang__dia_chi_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="diachigiaohang",
            name="kiem_tra__dia_chi_giao_hang__dia_chi_khong_rong",
        ),
        migrations.RemoveConstraint(
            model_name="diachigiaohang",
            name="kiem_tra__dia_chi_giao_hang__dia_chi_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="diachigiaohang",
            name="kiem_tra__dia_chi_giao_hang__ghi_chu_da_cat_khoang_trang",
        ),
        migrations.RemoveConstraint(
            model_name="diachigiaohang",
            name="kiem_tra__dia_chi_giao_hang__ghi_chu_mot_dong",
        ),
        migrations.RemoveConstraint(
            model_name="diachigiaohang",
            name="kiem_tra__dia_chi_giao_hang__so_dien_thoai_dung_dinh_dang",
        ),
        migrations.RemoveField(
            model_name="taikhoan",
            name="dia_chi_giao_hang_mac_dinh",
        ),
        migrations.DeleteModel(
            name="DiaChiGiaoHang",
        ),
    ]
