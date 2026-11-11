from django.db.models import Count, Q

from ung_dung.chung.permissions import kiem_tra_quyen, thay_toan_chuoi

from .models import NhatKyEmail


def lay_nhat_ky_email(nguoi):
    """Nhật ký email trong phạm vi được xem.

    Người có phạm vi toàn chuỗi thấy mọi thư. Nhân sự chi nhánh được giao quyền email.xem
    chỉ thấy thư về đơn của chi nhánh mình; thư tài khoản (mã xác thực, đổi mật khẩu...)
    không gắn đơn nên chỉ quản trị chuỗi xem được.
    """
    kiem_tra_quyen(nguoi, "email.xem")
    cac_email = NhatKyEmail.objects.select_related("tai_khoan", "don_hang__chi_nhanh")
    if not thay_toan_chuoi(nguoi):
        cac_email = cac_email.filter(don_hang__chi_nhanh_id=nguoi.chi_nhanh_id)
    return cac_email


def dem_theo_trang_thai(tap_hop, dieu_kien_ket):
    """Số thư lỗi, kẹt (chờ gửi quá lâu) và tổng của một tập nhật ký: một truy vấn."""
    return tap_hop.order_by().aggregate(
        loi=Count("pk", filter=Q(trang_thai="loi")),
        ket=Count("pk", filter=dieu_kien_ket & Q(trang_thai="cho_gui")),
        tong=Count("pk"),
    )
