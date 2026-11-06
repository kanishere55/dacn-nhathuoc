from uuid import uuid4

from django import forms

from ung_dung.danh_muc.models import ChiNhanh
from ung_dung.danh_muc.selectors import lay_chi_nhanh


class PhieuBanForm(forms.Form):
    chi_nhanh = forms.ModelChoiceField(ChiNhanh.objects.none(), label="Chi nhánh")
    khoa_yeu_cau = forms.UUIDField(widget=forms.HiddenInput, initial=uuid4)

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chi_nhanh"].queryset = lay_chi_nhanh(nguoi)
