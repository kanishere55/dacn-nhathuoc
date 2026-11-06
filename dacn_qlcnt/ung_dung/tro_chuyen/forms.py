from django import forms

from ung_dung.danh_muc.models import ChiNhanh


class MoPhongForm(forms.Form):
    chi_nhanh = forms.ModelChoiceField(
        ChiNhanh.objects.filter(dang_hoat_dong=True).order_by("ma_chi_nhanh"), label="Chi nhánh"
    )
