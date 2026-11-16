"""Bản nộp theo đề cương (Q45): chỉ chạy trên CSDL không có dữ liệu của phần mở rộng.

Các migration sau xóa bảng và cột của giao hàng, thanh toán trực tuyến và trả hàng. Nếu CSDL đang
có dữ liệu thật của những phần này (CSDL của bản đầy đủ) thì dừng lại, để không làm mất dữ liệu.
"""

from django.db import migrations

LOI = (
    "CSDL này đang có dữ liệu của bản đầy đủ ({}). Bản nộp theo đề cương dùng CSDL riêng: "
    "tạo CSDL mới theo README rồi chạy lại migrate."
)


def _co_bang(cursor, ten):
    cursor.execute("SELECT to_regclass(%s) IS NOT NULL", [f"public.{ten}"])
    return cursor.fetchone()[0]


def _co_cot(cursor, bang, cot):
    cursor.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s AND column_name = %s)",
        [bang, cot],
    )
    return cursor.fetchone()[0]


def _co_dong(cursor, cau_lenh):
    cursor.execute(f"SELECT EXISTS ({cau_lenh})")
    return cursor.fetchone()[0]


def kiem_tra(apps, schema_editor):
    phat_hien = []
    with schema_editor.connection.cursor() as cursor:
        if _co_cot(cursor, "don_hang", "hinh_thuc_nhan") and _co_dong(
            cursor, "SELECT 1 FROM don_hang WHERE hinh_thuc_nhan <> 'nhan_tai_quay'"
        ):
            phat_hien.append("đơn giao hàng")
        for bang, nhan in (
            ("yeu_cau_tra_hang", "yêu cầu trả hàng"),
            ("phieu_hoan_kho", "phiếu hoàn kho"),
            ("dia_chi_giao_hang", "sổ địa chỉ giao hàng"),
            ("giao_dich_cong_den", "giao dịch cổng thanh toán"),
        ):
            if _co_bang(cursor, bang) and _co_dong(cursor, f"SELECT 1 FROM {bang}"):
                phat_hien.append(nhan)
        if _co_bang(cursor, "giao_dich_thanh_toan") and _co_dong(
            cursor,
            "SELECT 1 FROM giao_dich_thanh_toan WHERE loai_giao_dich <> 'thu' "
            "OR phuong_thuc NOT IN ('tien_mat', 'chuyen_khoan') OR id_phieu_ban IS NULL",
        ):
            phat_hien.append("thanh toán trực tuyến hoặc hoàn tiền")
    if phat_hien:
        raise RuntimeError(LOI.format(", ".join(phat_hien)))


class Migration(migrations.Migration):
    dependencies = [("ban_hang", "0016_chuan_hoa_chi_muc_hang_tra")]
    operations = [migrations.RunPython(kiem_tra, migrations.RunPython.noop)]
