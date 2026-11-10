from django import forms

from ung_dung.danh_muc.models import ChiNhanh


class MoPhongForm(forms.Form):
    """Khách mở phòng tư vấn với một nhà thuốc, có thể gõ luôn câu hỏi đầu tiên."""

    chi_nhanh = forms.ModelChoiceField(
        ChiNhanh.objects.filter(dang_hoat_dong=True).order_by("ten_chi_nhanh"),
        label="Hỏi nhà thuốc",
        empty_label="Chọn nhà thuốc",
    )
    noi_dung = forms.CharField(
        label="Câu hỏi của bạn",
        required=False,
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Ví dụ: Bé 5 tuổi bị sốt thì dùng thuốc nào? Nhà thuốc còn Panadol không?",
            }
        ),
    )
