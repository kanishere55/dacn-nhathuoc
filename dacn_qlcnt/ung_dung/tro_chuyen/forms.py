from django import forms

from ung_dung.danh_muc.models import ChiNhanh


def _o_noi_dung(nhan, goi_y):
    return forms.CharField(
        label=nhan,
        max_length=2000,
        error_messages={"required": "Hãy nhập nội dung tin nhắn."},
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": goi_y}),
    )


class MoPhongForm(forms.Form):
    """Khách hỏi một nhà thuốc. Bắt buộc có câu hỏi: cuộc trò chuyện chỉ sinh ra khi có tin."""

    chi_nhanh = forms.ModelChoiceField(
        ChiNhanh.objects.filter(dang_hoat_dong=True).order_by("ten_chi_nhanh"),
        label="Hỏi nhà thuốc",
        empty_label="Chọn nhà thuốc",
    )
    noi_dung = _o_noi_dung(
        "Câu hỏi của bạn",
        "Ví dụ: Bé 5 tuổi bị sốt thì dùng thuốc nào? Nhà thuốc còn Panadol không?",
    )


class TinDauVeDonForm(forms.Form):
    """Tin đầu tiên về một đơn; gửi xong mới có cuộc trò chuyện ở hai phía."""

    noi_dung = _o_noi_dung("Tin nhắn", "")
