from django import forms

from ung_dung.chung.truong_form import TruongEmail, TruongPhongPhu, TruongSoDienThoai

from .models import BannerTrangChu, ThongTinCuaHang, TinTuc, TrangNoiDung


class _CatKhoangTrang:
    def clean(self):
        du_lieu = super().clean()
        for ten, gia_tri in du_lieu.items():
            if isinstance(gia_tri, str) and ten not in ("noi_dung_trang", "noi_dung_tin_tuc"):
                du_lieu[ten] = gia_tri.strip()
        return du_lieu


class BannerForm(_CatKhoangTrang, forms.ModelForm):
    anh = forms.ImageField(
        label="Ảnh banner",
        required=False,
        help_text="Ảnh ngang, tối thiểu 1200 px, đúng chủ đề nhà thuốc; nén WebP khi lưu.",
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
    )

    class Meta:
        model = BannerTrangChu
        fields = [
            "tieu_de",
            "mo_ta",
            "nhan_nut",
            "duong_dan",
            "mau_nen",
            "nguon_anh",
            "thu_tu",
            "dang_hien_thi",
            "ngay_bat_dau",
            "ngay_ket_thuc",
        ]
        labels = {
            "tieu_de": "Tiêu đề",
            "mo_ta": "Mô tả ngắn",
            "nhan_nut": "Chữ trên nút",
            "duong_dan": "Đường dẫn khi bấm",
            "mau_nen": "Màu nền",
            "nguon_anh": "Nguồn ảnh",
            "thu_tu": "Thứ tự",
            "dang_hien_thi": "Đang hiển thị",
            "ngay_bat_dau": "Hiện từ ngày",
            "ngay_ket_thuc": "Hiện đến ngày",
        }
        help_texts = {
            "duong_dan": "Đường dẫn trong website, ví dụ /thuoc/?danh_muc=VITAMIN",
            "nguon_anh": "Ví dụ: StockSnap, giấy phép CC0",
        }
        widgets = {
            "tieu_de": forms.TextInput(attrs={"maxlength": 80}),
            "mo_ta": forms.TextInput(attrs={"maxlength": 160}),
            "nhan_nut": forms.TextInput(attrs={"maxlength": 40}),
            "duong_dan": forms.TextInput(attrs={"placeholder": "/thuoc/"}),
            "mau_nen": forms.TextInput(attrs={"type": "color"}),
            "nguon_anh": forms.TextInput(),
            "ngay_bat_dau": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "ngay_ket_thuc": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def clean_mau_nen(self):
        return self.cleaned_data["mau_nen"].strip().lower()

    def clean(self):
        du_lieu = super().clean()
        if not self.instance.pk and not du_lieu.get("anh"):
            self.add_error("anh", "Banner mới cần ảnh.")
        return du_lieu


class ThongTinCuaHangForm(_CatKhoangTrang, forms.ModelForm):
    hotline = TruongSoDienThoai(label="Hotline", loai="hotline")
    email_lien_he = TruongEmail(label="Email liên hệ")

    class Meta:
        model = ThongTinCuaHang
        fields = [
            "ten_thuong_hieu",
            "khau_hieu",
            "hotline",
            "email_lien_he",
            "dia_chi_tru_so",
            "gio_lam_viec",
            "giay_phep_kinh_doanh",
        ]
        labels = {
            "ten_thuong_hieu": "Tên thương hiệu",
            "khau_hieu": "Khẩu hiệu",
            "hotline": "Hotline",
            "email_lien_he": "Email liên hệ",
            "dia_chi_tru_so": "Địa chỉ trụ sở",
            "gio_lam_viec": "Giờ phục vụ",
            "giay_phep_kinh_doanh": "Giấy chứng nhận đủ điều kiện kinh doanh dược",
        }
        widgets = {ten: forms.TextInput() for ten in fields}


class TrangNoiDungForm(_CatKhoangTrang, forms.ModelForm):
    noi_dung_trang = TruongPhongPhu(label="Nội dung")

    class Meta:
        model = TrangNoiDung
        fields = [
            "tieu_de",
            "duong_dan_trang",
            "tom_tat",
            "noi_dung_trang",
            "thu_tu",
            "dang_hien_thi",
        ]
        labels = {
            "tieu_de": "Tiêu đề",
            "duong_dan_trang": "Đường dẫn",
            "tom_tat": "Tóm tắt",
            "thu_tu": "Thứ tự ở chân trang",
            "dang_hien_thi": "Đang hiển thị",
        }
        help_texts = {
            "duong_dan_trang": "Chữ thường không dấu, nối bằng gạch ngang: chinh-sach-doi-tra"
        }
        widgets = {
            "tieu_de": forms.TextInput(),
            "duong_dan_trang": forms.TextInput(),
            "tom_tat": forms.TextInput(),
        }


class TinTucForm(_CatKhoangTrang, forms.ModelForm):
    noi_dung_tin_tuc = TruongPhongPhu(label="Nội dung")

    class Meta:
        model = TinTuc
        fields = [
            "tieu_de",
            "duong_dan_tin_tuc",
            "tom_tat",
            "noi_dung_tin_tuc",
            "thoi_diem_dang",
            "dang_hien_thi",
        ]
        labels = {
            "tieu_de": "Tiêu đề",
            "duong_dan_tin_tuc": "Đường dẫn",
            "tom_tat": "Tóm tắt",
            "thoi_diem_dang": "Thời điểm đăng",
            "dang_hien_thi": "Đang hiển thị",
        }
        help_texts = {
            "duong_dan_tin_tuc": "Chữ thường không dấu, nối bằng gạch ngang: phong-cum-mua-mua",
            "thoi_diem_dang": "Để trống là đăng ngay; chọn thời điểm sau này để hẹn giờ.",
        }
        widgets = {
            "tieu_de": forms.TextInput(attrs={"maxlength": 120}),
            "duong_dan_tin_tuc": forms.TextInput(),
            "tom_tat": forms.TextInput(attrs={"maxlength": 240}),
            "thoi_diem_dang": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["thoi_diem_dang"].required = False
