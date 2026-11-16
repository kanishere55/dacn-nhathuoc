import re
from uuid import uuid4

from django import forms

from ung_dung.chung.truong_form import TruongEmail, TruongMotDong
from ung_dung.danh_muc.models import ChiNhanh
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from .gio_hang import SO_LUONG_TOI_DA
from .models import KY_HIEU_HOA_DON, MA_SO_THUE, PHUONG_THUC_TAI_QUAY, SO_HOA_DON


class DonThuocForm(forms.Form):
    """Thông tin đơn thuốc dược sĩ ghi khi bán thuốc kê đơn; service kiểm bắt buộc."""

    da_kiem_tra_don_thuoc = forms.BooleanField(
        label="Đã kiểm tra đơn thuốc của bác sĩ", required=False
    )
    ten_nguoi_ke_don = TruongMotDong(label="Bác sĩ kê đơn", max_length=120, required=False)
    noi_kham_benh = TruongMotDong(label="Cơ sở khám bệnh", max_length=200, required=False)
    ma_don_thuoc = TruongMotDong(
        label="Mã đơn thuốc điện tử",
        max_length=30,
        required=False,
        help_text="Ghi khi đơn có mã liên thông; đơn giấy không mã thì để trống.",
    )
    ho_ten_nguoi_benh = TruongMotDong(label="Họ tên người bệnh", max_length=120, required=False)
    ngay_ke_don = forms.DateField(
        label="Ngày kê đơn",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        help_text="Ngày ghi trên đơn thuốc, không sau hôm nay.",
    )

    def don_thuoc(self):
        return {ten: self.cleaned_data.get(ten) for ten in DonThuocForm.base_fields}


class PhieuBanForm(DonThuocForm):
    chi_nhanh = forms.ModelChoiceField(
        ChiNhanh.objects.none(), label="Chi nhánh", empty_label="Chọn chi nhánh bán"
    )
    khoa_yeu_cau = forms.UUIDField(widget=forms.HiddenInput, initial=uuid4)
    phuong_thuc_thanh_toan = forms.ChoiceField(
        label="Khách trả bằng", choices=PHUONG_THUC_TAI_QUAY, initial="tien_mat"
    )
    field_order = ["chi_nhanh", "phuong_thuc_thanh_toan"]

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        cac_chi_nhanh = lay_chi_nhanh(nguoi)
        truong = self.fields["chi_nhanh"]
        truong.queryset = cac_chi_nhanh
        hai_chi_nhanh = list(cac_chi_nhanh[:2])
        self.chi_nhanh_mac_dinh = hai_chi_nhanh[0] if len(hai_chi_nhanh) == 1 else None
        if self.chi_nhanh_mac_dinh:
            self.initial["chi_nhanh"] = self.chi_nhanh_mac_dinh.pk
            truong.widget = forms.HiddenInput()


class SuaSoLuongGioForm(forms.Form):
    so_luong = forms.IntegerField(label="Số lượng", min_value=0, max_value=SO_LUONG_TOI_DA)


class ThemThuocVaoGioForm(forms.Form):
    so_luong = forms.IntegerField(label="Số lượng", min_value=1, max_value=SO_LUONG_TOI_DA)


class DatHangForm(forms.Form):
    """Lựa chọn khi đặt giữ; chi nhánh còn đủ hàng do view và service kiểm lại."""

    chi_nhanh = forms.IntegerField(required=False, widget=forms.HiddenInput)
    # Vị trí hiện tại của khách (định vị trình duyệt), chỉ để sắp chi nhánh gần trước.
    vi_do = forms.FloatField(required=False, min_value=8.0, max_value=23.5)
    kinh_do = forms.FloatField(required=False, min_value=102.0, max_value=110.0)
    # Nhãn của vị trí (địa chỉ khách gõ và chọn, hoặc "vị trí hiện tại") để hiện lại sau mỗi lần cập nhật.
    nhan_vi_tri = TruongMotDong(max_length=200, required=False)
    ghi_chu_khach = TruongMotDong(label="Lời nhắn cho nhà thuốc", max_length=300, required=False)
    # Tổng tiền khách đang nhìn thấy khi bấm đặt; khác tổng tính lại thì không tạo đơn.
    tong_da_xem = forms.IntegerField(required=False, min_value=0, widget=forms.HiddenInput)


class XuLyDonForm(DonThuocForm):
    ly_do = TruongMotDong(label="Lý do", max_length=300, required=False)
    phuong_thuc_thanh_toan = forms.ChoiceField(
        choices=PHUONG_THUC_TAI_QUAY, required=False, initial="tien_mat"
    )


class YeuCauXuatHoaDonForm(forms.Form):
    ten_cong_ty = TruongMotDong(label="Tên công ty", max_length=300)
    ma_so_thue = TruongMotDong(
        label="Mã số thuế", max_length=14, help_text="10 chữ số; chi nhánh doanh nghiệp thêm -XXX."
    )
    dia_chi_cong_ty = TruongMotDong(label="Địa chỉ theo đăng ký thuế", max_length=300)
    email_nhan_hoa_don = TruongEmail(label="Email nhận hóa đơn")

    def clean_ma_so_thue(self):
        ma = re.sub(r"\s+", "", self.cleaned_data["ma_so_thue"])
        if not re.fullmatch(MA_SO_THUE, ma):
            raise forms.ValidationError("Mã số thuế gồm 10 chữ số, hoặc 10 chữ số kèm -XXX.")
        return ma


class XuLyXuatHoaDonForm(forms.Form):
    trang_thai = forms.ChoiceField(
        label="Kết quả", choices=[("da_xuat", "Đã xuất hóa đơn"), ("tu_choi", "Từ chối")]
    )
    ky_hieu_hoa_don = TruongMotDong(
        label="Ký hiệu hóa đơn",
        max_length=7,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "1C26TAA", "autocomplete": "off"}),
    )
    so_hoa_don = TruongMotDong(
        label="Số hóa đơn",
        max_length=8,
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "0000123", "inputmode": "numeric", "autocomplete": "off"}
        ),
    )
    ly_do_tu_choi = TruongMotDong(label="Lý do từ chối", max_length=500, required=False)

    def clean(self):
        du_lieu = super().clean()
        if du_lieu.get("trang_thai") == "da_xuat":
            du_lieu["ky_hieu_hoa_don"] = (du_lieu.get("ky_hieu_hoa_don") or "").upper()
            if not re.fullmatch(KY_HIEU_HOA_DON, du_lieu["ky_hieu_hoa_don"]):
                self.add_error(
                    "ky_hieu_hoa_don", "Ký hiệu gồm 7 ký tự như trên hóa đơn, ví dụ 1C26TAA."
                )
            if not re.fullmatch(SO_HOA_DON, du_lieu.get("so_hoa_don") or ""):
                self.add_error("so_hoa_don", "Số hóa đơn gồm 1 đến 8 chữ số.")
        elif du_lieu.get("trang_thai") == "tu_choi" and not du_lieu.get("ly_do_tu_choi"):
            self.add_error("ly_do_tu_choi", "Ghi lý do từ chối để khách nắm được.")
        return du_lieu
