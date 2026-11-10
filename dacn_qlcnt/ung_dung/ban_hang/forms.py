import re
from uuid import uuid4

from django import forms

from ung_dung.chung.ten_csdl import EMAIL
from ung_dung.chung.truong_form import TruongMotDong, TruongSoDienThoai
from ung_dung.danh_muc.forms import NhieuTepInput, TruongNhieuTep
from ung_dung.danh_muc.models import ChiNhanh
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from .gio_hang import SO_LUONG_TOI_DA
from .models import (
    HINH_THUC_HOAN_TIEN,
    HINH_THUC_NHAN,
    LY_DO_TRA_HANG,
    MA_SO_THUE,
    PHUONG_THUC_THANH_TOAN,
)

PHUONG_THUC_TAI_QUAY = [("tien_mat", "Tiền mặt"), ("chuyen_khoan", "Chuyển khoản")]


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
    """Lựa chọn khi đặt hàng; hợp lệ với giỏ và chi nhánh do view và service kiểm lại."""

    hinh_thuc_nhan = forms.ChoiceField(choices=HINH_THUC_NHAN, widget=forms.RadioSelect)
    dia_chi = forms.IntegerField(required=False, widget=forms.HiddenInput)
    chi_nhanh = forms.IntegerField(required=False, widget=forms.HiddenInput)
    phuong_thuc_thanh_toan = forms.ChoiceField(
        choices=PHUONG_THUC_THANH_TOAN, required=False, widget=forms.RadioSelect
    )
    ghi_chu_khach = TruongMotDong(label="Lời nhắn cho nhà thuốc", max_length=300, required=False)


class XuLyDonForm(DonThuocForm):
    ly_do = TruongMotDong(label="Lý do", max_length=300, required=False)
    phuong_thuc_thanh_toan = forms.ChoiceField(
        choices=PHUONG_THUC_TAI_QUAY, required=False, initial="tien_mat"
    )
    ma_tham_chieu = TruongMotDong(label="Mã giao dịch", max_length=64, required=False)
    phuong_thuc_hoan = forms.ChoiceField(
        choices=[*PHUONG_THUC_TAI_QUAY, ("momo", "Ví MoMo")], required=False
    )

    def clean_ma_tham_chieu(self):
        ma = self.cleaned_data["ma_tham_chieu"]
        if ma and not re.fullmatch(r"[A-Za-z0-9._:/-]{1,58}", ma):
            raise forms.ValidationError("Mã giao dịch chỉ gồm chữ, số và . _ : / -")
        return ma


def chu_in_hoa_khong_dau(chuoi):
    """Tên chủ tài khoản ngân hàng in trên thẻ: chữ in hoa, không dấu, một khoảng trắng."""
    import unicodedata

    chuoi = (chuoi or "").replace("đ", "d").replace("Đ", "D")
    khong_dau = "".join(
        ky_tu
        for ky_tu in unicodedata.normalize("NFD", chuoi)
        if unicodedata.category(ky_tu) != "Mn"
    )
    return " ".join(re.sub(r"[^A-Za-z ]", " ", khong_dau).upper().split())


class TraHangForm(forms.Form):
    """Khách chọn số lượng trả cho từng dòng đơn, lý do, mô tả và ảnh minh chứng."""

    ly_do = forms.ChoiceField(label="Lý do", choices=LY_DO_TRA_HANG, widget=forms.RadioSelect)
    mo_ta = forms.CharField(
        label="Mô tả tình trạng",
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Ví dụ: hộp bị móp, vỉ thuốc rách"}),
    )
    cac_anh = TruongNhieuTep(
        label="Ảnh chụp thuốc và bao bì",
        widget=NhieuTepInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        error_messages={"required": "Cần ít nhất một ảnh chụp tình trạng thuốc."},
    )

    hinh_thuc_hoan_tien = forms.ChoiceField(
        label="Nhận tiền hoàn qua",
        choices=HINH_THUC_HOAN_TIEN,
        initial="chuyen_khoan",
        widget=forms.RadioSelect,
    )
    ten_ngan_hang = TruongMotDong(
        label="Ngân hàng",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"list": "danh-sach-ngan-hang", "autocomplete": "off"}),
    )
    so_tai_khoan = TruongMotDong(
        label="Số tài khoản",
        max_length=19,
        required=False,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    ten_chu_tai_khoan = TruongMotDong(
        label="Tên chủ tài khoản",
        max_length=100,
        required=False,
        help_text="Viết đúng như trên thẻ, hệ thống tự đổi sang chữ in hoa không dấu.",
    )
    so_dien_thoai_momo = TruongSoDienThoai(label="Số điện thoại ví MoMo", required=False)

    def __init__(self, *args, cac_dong, con_lai, **kwargs):
        super().__init__(*args, **kwargs)
        self.cac_dong_don = []
        for dong in cac_dong:
            toi_da = con_lai.get(dong.pk, 0)
            if toi_da <= 0:
                continue
            ten = f"so_luong_{dong.pk}"
            self.fields[ten] = forms.IntegerField(
                label=dong.thuoc.ten_thuoc, min_value=0, max_value=toi_da, initial=0
            )
            self.cac_dong_don.append({"dong": dong, "o": self[ten], "toi_da": toi_da})

    def clean(self):
        du_lieu = super().clean()
        hinh_thuc = du_lieu.get("hinh_thuc_hoan_tien")
        if hinh_thuc == "chuyen_khoan":
            du_lieu["ten_chu_tai_khoan"] = chu_in_hoa_khong_dau(
                du_lieu.get("ten_chu_tai_khoan", "")
            )
            for ten, nhan in (
                ("ten_ngan_hang", "ngân hàng"),
                ("so_tai_khoan", "số tài khoản"),
                ("ten_chu_tai_khoan", "tên chủ tài khoản"),
            ):
                if not du_lieu.get(ten):
                    self.add_error(ten, f"Nhập {nhan} để nhà thuốc chuyển khoản hoàn tiền.")
            so_tk = re.sub(r"[\s.-]", "", du_lieu.get("so_tai_khoan") or "")
            if so_tk and not re.fullmatch(r"[0-9]{6,19}", so_tk):
                self.add_error("so_tai_khoan", "Số tài khoản gồm 6 đến 19 chữ số.")
            du_lieu["so_tai_khoan"] = so_tk
            du_lieu["so_dien_thoai_momo"] = ""
        elif hinh_thuc == "momo":
            if not du_lieu.get("so_dien_thoai_momo"):
                self.add_error("so_dien_thoai_momo", "Nhập số điện thoại đăng ký ví MoMo.")
            du_lieu.update(ten_ngan_hang="", so_tai_khoan="", ten_chu_tai_khoan="")
        else:
            du_lieu.update(
                ten_ngan_hang="", so_tai_khoan="", ten_chu_tai_khoan="", so_dien_thoai_momo=""
            )
        return du_lieu

    def thong_tin_hoan_tien(self):
        return {
            ten: self.cleaned_data.get(ten, "")
            for ten in (
                "hinh_thuc_hoan_tien",
                "ten_ngan_hang",
                "so_tai_khoan",
                "ten_chu_tai_khoan",
                "so_dien_thoai_momo",
            )
        }

    def cac_dong_tra(self):
        return {
            muc["dong"].pk: self.cleaned_data.get(f"so_luong_{muc['dong'].pk}") or 0
            for muc in self.cac_dong_don
        }


class XuLyTraHangForm(forms.Form):
    ghi_chu = TruongMotDong(label="Ghi chú", max_length=500, required=False)
    phuong_thuc = forms.ChoiceField(
        choices=[*PHUONG_THUC_TAI_QUAY, ("momo", "Ví MoMo")], required=False
    )
    ma_tham_chieu = TruongMotDong(label="Mã giao dịch", max_length=58, required=False)

    def clean_ma_tham_chieu(self):
        ma = self.cleaned_data["ma_tham_chieu"]
        if ma and not re.fullmatch(r"[A-Za-z0-9._:/-]{1,58}", ma):
            raise forms.ValidationError("Mã giao dịch chỉ gồm chữ, số và . _ : / -")
        return ma


class YeuCauXuatHoaDonForm(forms.Form):
    ten_cong_ty = TruongMotDong(label="Tên công ty", max_length=300)
    ma_so_thue = TruongMotDong(
        label="Mã số thuế", max_length=14, help_text="10 chữ số; chi nhánh doanh nghiệp thêm -XXX."
    )
    dia_chi_cong_ty = TruongMotDong(label="Địa chỉ theo đăng ký thuế", max_length=300)
    email_nhan_hoa_don = forms.EmailField(label="Email nhận hóa đơn", max_length=254)

    def clean_ma_so_thue(self):
        ma = re.sub(r"\s+", "", self.cleaned_data["ma_so_thue"])
        if not re.fullmatch(MA_SO_THUE, ma):
            raise forms.ValidationError("Mã số thuế gồm 10 chữ số, hoặc 10 chữ số kèm -XXX.")
        return ma

    def clean_email_nhan_hoa_don(self):
        email = self.cleaned_data["email_nhan_hoa_don"].strip().lower()
        if not re.fullmatch(EMAIL, email):
            raise forms.ValidationError("Email cần có tên miền đầy đủ, ví dụ ketoan@congty.vn.")
        return email


class XuLyXuatHoaDonForm(forms.Form):
    trang_thai = forms.ChoiceField(
        label="Kết quả", choices=[("da_xuat", "Đã xuất hóa đơn"), ("tu_choi", "Từ chối")]
    )
    ghi_chu_xu_ly = TruongMotDong(
        label="Ký hiệu, số hóa đơn hoặc lý do từ chối",
        max_length=500,
        widget=forms.TextInput(attrs={"placeholder": "Ví dụ: Ký hiệu 1C26TAA, số 0000123"}),
    )
