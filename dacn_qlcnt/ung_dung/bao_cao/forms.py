from datetime import timedelta

from django import forms
from django.utils import timezone

from ung_dung.danh_muc.models import ChiNhanh
from ung_dung.danh_muc.selectors import lay_chi_nhanh


class LocBaoCaoForm(forms.Form):
    chi_nhanh = forms.ModelChoiceField(
        ChiNhanh.objects.none(),
        label="Chi nhánh",
        required=False,
        empty_label="Tất cả trong phạm vi",
    )
    tu_ngay = forms.DateField(label="Từ ngày", widget=forms.DateInput(attrs={"type": "date"}))
    den_ngay = forms.DateField(label="Đến ngày", widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, nguoi, **kwargs):
        hom_nay = timezone.localdate()
        kwargs.setdefault("initial", {"tu_ngay": hom_nay - timedelta(days=29), "den_ngay": hom_nay})
        super().__init__(*args, **kwargs)
        self.fields["chi_nhanh"].queryset = lay_chi_nhanh(nguoi, ca_chi_nhanh_ngung=True)

    def clean(self):
        du_lieu = super().clean()
        tu_ngay, den_ngay = du_lieu.get("tu_ngay"), du_lieu.get("den_ngay")
        if (
            tu_ngay
            and den_ngay
            and (den_ngay < tu_ngay or den_ngay >= timezone.localdate() + timedelta(days=1))
        ):
            self.add_error("den_ngay", "Đến ngày phải từ ngày bắt đầu đến hôm nay.")
        return du_lieu
