"""Bổ sung quyền mới vào nhóm "Quản lý chi nhánh (mặc định)" đã có sẵn trong CSDL.

Commit 30826ef thêm `thanh_toan.xac_nhan` (ghi nhận tiền chuyển khoản/COD) và
`thuoc_ke_don.ban` vào MAC_DINH của quản lý chi nhánh. `bao_dam_nhom_mac_dinh` chỉ ghi quyền
khi tạo nhóm lần đầu, nên CSDL đã có nhóm từ trước không nhận hai quyền này và quản lý chi
nhánh không thấy nút "Đã nhận tiền COD". Migration chỉ thêm, không xóa quyền quản trị đã chỉnh.
"""

from django.db import migrations

QUYEN_MOI = ("thanh_toan.xac_nhan", "thuoc_ke_don.ban")


def bo_sung(apps, schema_editor):
    NhomQuyen = apps.get_model("tai_khoan", "NhomQuyen")
    QuyenCuaNhom = apps.get_model("tai_khoan", "QuyenCuaNhom")
    for nhom in NhomQuyen.objects.filter(vai_tro_mac_dinh="quan_ly_chi_nhanh"):
        da_co = set(QuyenCuaNhom.objects.filter(nhom_quyen=nhom).values_list("ma_quyen", flat=True))
        QuyenCuaNhom.objects.bulk_create(
            QuyenCuaNhom(nhom_quyen=nhom, ma_quyen=ma) for ma in QUYEN_MOI if ma not in da_co
        )


class Migration(migrations.Migration):
    dependencies = [("tai_khoan", "0013_chuan_hoa_ten_csdl")]

    operations = [migrations.RunPython(bo_sung, migrations.RunPython.noop)]
