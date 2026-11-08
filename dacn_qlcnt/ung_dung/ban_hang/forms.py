from uuid import uuid4

from django import forms

from ung_dung.danh_muc.models import ChiNhanh
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from .gio_dat_giu import SO_LUONG_TOI_DA


class PhieuBanForm(forms.Form):
    chi_nhanh = forms.ModelChoiceField(ChiNhanh.objects.none(), label="Chi nhánh")
    khoa_yeu_cau = forms.UUIDField(widget=forms.HiddenInput, initial=uuid4)

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chi_nhanh"].queryset = lay_chi_nhanh(nguoi)


class SuaSoLuongGioForm(forms.Form):
    so_luong = forms.IntegerField(label="Số lượng", min_value=0, max_value=SO_LUONG_TOI_DA)


class ThemThuocVaoGioForm(forms.Form):
    so_luong = forms.IntegerField(label="Số lượng", min_value=1, max_value=SO_LUONG_TOI_DA)


class ChonChiNhanhGiuForm(forms.Form):
    chi_nhanh = forms.ModelChoiceField(
        ChiNhanh.objects.none(), label="Chi nhánh nhận thuốc", empty_label="Chọn chi nhánh"
    )

    def __init__(self, *args, cac_chi_nhanh, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chi_nhanh"].queryset = cac_chi_nhanh
