from django import forms

from ung_dung.danh_muc.forms import NhieuTepInput, TruongNhieuTep
from ung_dung.danh_muc.models import ChiNhanh

from .models import SO_ANH_TOI_DA

KIEU_ANH = "image/jpeg,image/png,image/webp,image/gif"


def _o_noi_dung(nhan, goi_y):
    o = forms.CharField(
        label=nhan,
        max_length=2000,
        required=False,
        strip=False,
        error_messages={"max_length": "Tin nhắn tối đa %(limit_value)d ký tự."},
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": goi_y}),
    )
    # Không bắt buộc vì tin có thể chỉ gồm ảnh, nhưng không ghi "(tùy chọn)": thiếu cả chữ lẫn
    # ảnh vẫn bị báo lỗi.
    o.an_tuy_chon = True
    return o


def _o_anh():
    return TruongNhieuTep(
        label="Ảnh đính kèm",
        required=False,
        help_text=f"Tối đa {SO_ANH_TOI_DA} ảnh JPEG, PNG, WebP hoặc GIF.",
        widget=NhieuTepInput(attrs={"accept": KIEU_ANH, "data-chon-anh": "", "class": "sr-only"}),
    )


class _CoNoiDungHoacAnh(forms.Form):
    """Tin phải có chữ hoặc ít nhất một ảnh; tối đa 5 ảnh."""

    # Ô ảnh do JS giữ danh sách nên có thể trống lúc gửi; máy chủ vẫn kiểm.
    use_required_attribute = False

    def clean(self):
        du_lieu = super().clean()
        cac_anh = [tep for tep in du_lieu.get("cac_anh") or [] if tep]
        if len(cac_anh) > SO_ANH_TOI_DA:
            self.add_error("cac_anh", f"Mỗi tin gửi tối đa {SO_ANH_TOI_DA} ảnh.")
        du_lieu["cac_anh"] = cac_anh
        if not (du_lieu.get("noi_dung") or "").strip() and not cac_anh and not self.errors:
            self.add_error("noi_dung", "Hãy nhập nội dung tin nhắn hoặc chọn ảnh.")
        return du_lieu


class MoPhongForm(_CoNoiDungHoacAnh):
    """Khách nhắn một nhà thuốc. Đã từng nhắn nhà thuốc đó thì tin nối vào cuộc trò chuyện cũ."""

    chi_nhanh = forms.ModelChoiceField(
        ChiNhanh.objects.filter(dang_hoat_dong=True).order_by("ten_chi_nhanh"),
        label="Nhắn tới nhà thuốc",
        empty_label="Chọn nhà thuốc",
        error_messages={
            "required": "Hãy chọn nhà thuốc muốn hỏi.",
            "invalid_choice": "Nhà thuốc đã chọn không còn hoạt động, hãy chọn nhà thuốc khác.",
        },
    )
    noi_dung = _o_noi_dung(
        "Câu hỏi của bạn",
        "Ví dụ: Bé 5 tuổi bị sốt thì dùng thuốc nào? Nhà thuốc còn Panadol không?",
    )
    cac_anh = _o_anh()


class TinDauVeDonForm(_CoNoiDungHoacAnh):
    """Tin đầu tiên về một đơn khi khách và chi nhánh của đơn chưa từng trò chuyện."""

    noi_dung = _o_noi_dung("Tin nhắn", "")
    cac_anh = _o_anh()


class GuiTinForm(_CoNoiDungHoacAnh):
    """Tin kèm ảnh trong cuộc trò chuyện đang mở (tin chỉ có chữ đi qua WebSocket)."""

    ma_tin_nhan = forms.UUIDField(error_messages={"invalid": "Mã tin nhắn không hợp lệ."})
    noi_dung = _o_noi_dung("Tin nhắn", "")
    cac_anh = _o_anh()
    thuoc = forms.IntegerField(required=False, min_value=1)
    don_hang = forms.IntegerField(required=False, min_value=1)
