"""Chống lập trùng chứng từ kho khi bấm lưu hai lần hoặc trình duyệt gửi lại form.

Form cấp một UUID ẩn (khoa_yeu_cau) mỗi lần mở. Service gọi `phieu_da_luu` sau khi đã khóa
kho: hai yêu cầu cùng khóa chạy nối tiếp nhau, yêu cầu sau thấy phiếu của yêu cầu trước và
trả lại đúng phiếu đó. Ràng buộc UNIQUE trên cột khoa_yeu_cau là lớp chặn cuối ở CSDL.
"""

from django.core.exceptions import ValidationError

from ..models.chung import tao_khoa_yeu_cau


def chuan_hoa_khoa(khoa_yeu_cau):
    return str(khoa_yeu_cau) if khoa_yeu_cau else tao_khoa_yeu_cau()


def phieu_da_luu(model, khoa_yeu_cau, nguoi, **cung_gia_tri):
    """Phiếu đã lập từ cùng form (cùng người lập, cùng chi nhánh...), hoặc None."""
    if not khoa_yeu_cau:
        return None
    phieu = model.objects.filter(khoa_yeu_cau=str(khoa_yeu_cau)).first()
    if phieu is None:
        return None
    if phieu.nguoi_lap_id != nguoi.pk or any(
        getattr(phieu, f"{ten}_id") != gia_tri.pk for ten, gia_tri in cung_gia_tri.items()
    ):
        raise ValidationError(
            "Biểu mẫu này đã được dùng để lập một phiếu khác. Hãy mở lại trang rồi nhập lại."
        )
    return phieu
