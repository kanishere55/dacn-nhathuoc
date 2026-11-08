from uuid import uuid4

from django import forms

from ung_dung.chung.truong_form import TruongMotDong
from ung_dung.danh_muc.models import ChiNhanh
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from .gio_hang import SO_LUONG_TOI_DA
from .models import HINH_THUC_NHAN, PHUONG_THUC_THANH_TOAN


class PhieuBanForm(forms.Form):
    chi_nhanh = forms.ModelChoiceField(ChiNhanh.objects.none(), label="Chi nhánh")
    khoa_yeu_cau = forms.UUIDField(widget=forms.HiddenInput, initial=uuid4)
    da_kiem_tra_don_thuoc = forms.BooleanField(
        label="Đã kiểm tra đơn thuốc của bác sĩ (bắt buộc nếu có thuốc kê đơn)", required=False
    )

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chi_nhanh"].queryset = lay_chi_nhanh(nguoi)


class SuaSoLuongGioForm(forms.Form):
    so_luong = forms.IntegerField(label="Số lượng", min_value=0, max_value=SO_LUONG_TOI_DA)


class ThemThuocVaoGioForm(forms.Form):
    so_luong = forms.IntegerField(label="Số lượng", min_value=1, max_value=SO_LUONG_TOI_DA)


class DatHangForm(forms.Form):
    """Lựa chọn khi đặt hàng; hợp lệ với giỏ và chi nhánh do view và service kiểm lại."""

    hinh_thuc_nhan = forms.ChoiceField(choices=HINH_THUC_NHAN, widget=forms.RadioSelect)
    dia_chi = forms.IntegerField(required=False, widget=forms.HiddenInput)
    chi_nhanh = forms.IntegerField(required=False, widget=forms.HiddenInput)
    phuong_thuc_thanh_toan = forms.ChoiceField(
        choices=PHUONG_THUC_THANH_TOAN, required=False, widget=forms.RadioSelect
    )
    ghi_chu_khach = TruongMotDong(label="Lời nhắn cho nhà thuốc", max_length=300, required=False)


class XuLyDonForm(forms.Form):
    ly_do = TruongMotDong(label="Lý do", max_length=300, required=False)
    da_kiem_tra_don_thuoc = forms.BooleanField(required=False)
