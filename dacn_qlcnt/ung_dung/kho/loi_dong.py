"""Lỗi theo dòng của phiếu kho: service chỉ ra dòng và ô sai, view gắn lỗi vào đúng chỗ đó."""

from django.core.exceptions import ValidationError


class LoiDongPhieu(ValidationError):
    """`cac_loi_dong` là danh sách (chỉ số dòng trong cac_dong của service, tên ô, câu báo).

    Vẫn là ValidationError nên nơi gọi chỉ cần câu chung (lệnh, test) vẫn đọc được,
    mỗi câu kèm "Dòng N".
    """

    def __init__(self, cac_loi_dong):
        self.cac_loi_dong = list(cac_loi_dong)
        super().__init__([f"Dòng {chi_so + 1}: {cau}" for chi_so, _, cau in self.cac_loi_dong])


def cac_dong_da_nhap(formset):
    """(form, dữ liệu) của các dòng có nhập và không bị bỏ, đúng thứ tự gửi vào service."""
    return [
        (form, form.cleaned_data)
        for form in formset.forms
        if form.cleaned_data and not form.cleaned_data.get("DELETE")
    ]


def gan_loi(form, cac_form_dong, loi):
    """Đưa lỗi từ service vào ô của dòng tương ứng; lỗi chung của phiếu đặt ở đầu form."""
    if not isinstance(loi, LoiDongPhieu):
        form.add_error(None, loi)
        return
    for chi_so, ten_o, cau in loi.cac_loi_dong:
        if chi_so < len(cac_form_dong):
            dong = cac_form_dong[chi_so]
            dong.add_error(ten_o if ten_o in dong.fields else None, cau)
        else:
            form.add_error(None, f"Dòng {chi_so + 1}: {cau}")
    so_dong = len({chi_so for chi_so, _, _ in loi.cac_loi_dong})
    form.add_error(
        None,
        f"Phiếu chưa được lưu: {so_dong} dòng cần sửa, xem các dòng tô đỏ trong bảng bên dưới.",
    )
