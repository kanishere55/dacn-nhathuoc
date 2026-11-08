from django import forms
from django.contrib.gis.geos import Point

from ung_dung.chung.van_ban import cat_khoang_trang

from .selectors import DANH_MUC

NHAN = {
    "ma_chi_nhanh": "Mã chi nhánh",
    "ten_chi_nhanh": "Tên chi nhánh",
    "dia_chi": "Địa chỉ",
    "dang_hoat_dong": "Đang hoạt động",
    "ma_don_vi_tinh": "Mã đơn vị",
    "ten_don_vi_tinh": "Tên đơn vị",
    "ma_nhom_atc": "Mã ATC",
    "ten_nhom_atc": "Diễn giải ATC",
    "ma_nha_cung_cap": "Mã nhà cung cấp",
    "ten_nha_cung_cap": "Tên nhà cung cấp",
    "so_dien_thoai": "Số điện thoại",
    "ma_thuoc": "Mã thuốc",
    "ten_thuoc": "Tên thuốc",
    "nhom_atc": "Nhóm ATC",
    "don_vi_tinh": "Đơn vị cơ sở",
    "ham_luong": "Hàm lượng",
    "dang_bao_che": "Dạng bào chế",
    "nha_san_xuat": "Nhà sản xuất",
    "gia_ban": "Giá bán / đơn vị cơ sở (VND)",
    "nguong_canh_bao": "Ngưỡng tồn thấp",
    "thuoc": "Thuốc",
    "ten_quy_doi_bao_goi": "Tên bao gói",
    "he_so": "Hệ số quy đổi",
    "ma_nhan_vien": "Mã nhân viên",
    "ten_nhan_vien": "Họ tên",
    "tai_khoan": "Tài khoản",
    "gio_mo_cua": "Giờ mở cửa",
    "gio_dong_cua": "Giờ đóng cửa",
    "danh_muc_san_pham": "Danh mục sản phẩm",
    "la_thuoc_ke_don": "Thuốc kê đơn (chỉ bán tại quầy khi có đơn)",
    "hoat_chat": "Hoạt chất",
    "quy_cach_dong_goi": "Quy cách đóng gói",
    "nuoc_san_xuat": "Nước sản xuất",
    "so_dang_ky": "Số đăng ký",
    "mo_ta_ngan": "Mô tả ngắn",
    "cong_dung": "Công dụng",
    "cach_dung": "Liều dùng và cách dùng",
    "chong_chi_dinh": "Chống chỉ định",
    "tac_dung_phu": "Tác dụng không mong muốn",
    "luu_y": "Thận trọng, lưu ý",
    "bao_quan": "Bảo quản",
    "ma_danh_muc_san_pham": "Mã danh mục",
    "ten_danh_muc_san_pham": "Tên danh mục",
    "mo_ta": "Mô tả",
    "bieu_tuong": "Biểu tượng (tên icon Lucide)",
    "thu_tu": "Thứ tự hiển thị",
    "dang_hien_thi": "Đang hiển thị",
    "ma_khuyen_mai": "Mã khuyến mãi",
    "ten_khuyen_mai": "Tên chương trình",
    "phan_tram_giam": "Giảm (%)",
    "ngay_bat_dau": "Từ ngày",
    "ngay_ket_thuc": "Đến ngày",
}
# Cột văn bản được nhập nhiều dòng; cột văn bản khác dùng ô một dòng.
NHIEU_DONG = {"cong_dung", "cach_dung", "chong_chi_dinh", "tac_dung_phu", "luu_y"}
# Ô một dòng thường dài, chiếm cả hàng trên form.
TRUONG_RONG = {"mo_ta_ngan", "hoat_chat", "dia_chi", "mo_ta", "ten_khuyen_mai"}
NHOM_TRUONG = {
    "thuoc": [
        (
            "Thông tin cơ bản",
            [
                "ma_thuoc",
                "ten_thuoc",
                "danh_muc_san_pham",
                "nhom_atc",
                "la_thuoc_ke_don",
                "dang_hoat_dong",
            ],
        ),
        (
            "Thành phần và quy cách",
            [
                "hoat_chat",
                "ham_luong",
                "dang_bao_che",
                "quy_cach_dong_goi",
                "don_vi_tinh",
                "nha_san_xuat",
                "nuoc_san_xuat",
                "so_dang_ky",
            ],
        ),
        ("Giá và tồn kho", ["gia_ban", "nguong_canh_bao"]),
        (
            "Nội dung hiển thị cho khách",
            [
                "mo_ta_ngan",
                "cong_dung",
                "cach_dung",
                "chong_chi_dinh",
                "tac_dung_phu",
                "luu_y",
                "bao_quan",
            ],
        ),
    ],
    "chi_nhanh": [
        (
            "Thông tin",
            ["ma_chi_nhanh", "ten_chi_nhanh", "dia_chi", "so_dien_thoai", "dang_hoat_dong"],
        ),
        ("Giờ mở cửa hằng ngày", ["gio_mo_cua", "gio_dong_cua"]),
        ("Tọa độ WGS84", ["kinh_do", "vi_do"]),
    ],
}


class FormDanhMuc(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for ten, truong in self.fields.items():
            if isinstance(truong.widget, forms.Textarea) and ten not in NHIEU_DONG:
                truong.widget = forms.TextInput()
            elif isinstance(truong.widget, forms.Textarea):
                truong.widget.attrs.update(rows=4)
            elif isinstance(truong, forms.DateField):
                truong.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
            elif isinstance(truong, forms.TimeField):
                truong.widget = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")

    def clean(self):
        du_lieu = super().clean()
        for ten, gia_tri in list(du_lieu.items()):
            if isinstance(gia_tri, str):
                du_lieu[ten] = cat_khoang_trang(gia_tri.replace("\r\n", "\n"))
        return du_lieu

    def cac_nhom(self):
        """Nhóm trường cho template; mô hình không khai báo nhóm thì gộp một nhóm."""
        nhom = NHOM_TRUONG.get(getattr(self, "loai", ""), [("", list(self.fields))])
        return [
            (
                tieu_de,
                [
                    (self[ten], ten in NHIEU_DONG or ten in TRUONG_RONG)
                    for ten in cac_ten
                    if ten in self.fields
                ],
            )
            for tieu_de, cac_ten in nhom
        ]


class NhieuTepInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class TruongNhieuTep(forms.FileField):
    """FileField nhận nhiều tệp cùng một ô, theo hướng dẫn của Django."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", NhieuTepInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        lam_sach = super().clean
        if isinstance(data, (list, tuple)):
            return [lam_sach(tep, initial) for tep in data]
        return [lam_sach(data, initial)]


class TaiAnhForm(forms.Form):
    cac_anh = TruongNhieuTep(
        label="Thêm ảnh",
        help_text="JPEG, PNG, WebP hoặc GIF; ảnh được nén WebP, cạnh dài tối đa 1600 px.",
        widget=NhieuTepInput(attrs={"accept": "image/jpeg,image/png,image/webp,image/gif"}),
        error_messages={"required": "Hãy chọn ít nhất một ảnh."},
    )


def lay_form(loai):
    model = DANH_MUC[loai][0]
    cac_cot = [
        cot.name for cot in model._meta.fields if not cot.primary_key and cot.name != "vi_tri"
    ]
    lop = forms.modelform_factory(model, form=FormDanhMuc, fields=cac_cot, labels=NHAN)
    lop.loai = loai
    if loai == "chi_nhanh":

        class FormChiNhanh(lop):
            kinh_do = forms.FloatField(label="Kinh độ", min_value=-180, max_value=180)
            vi_do = forms.FloatField(label="Vĩ độ", min_value=-90, max_value=90)

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if self.instance.pk:
                    self.initial.update(
                        kinh_do=self.instance.vi_tri.x, vi_do=self.instance.vi_tri.y
                    )

            def clean(self):
                du_lieu = super().clean()
                if "kinh_do" in du_lieu and "vi_do" in du_lieu:
                    du_lieu["vi_tri"] = Point(
                        du_lieu.pop("kinh_do"), du_lieu.pop("vi_do"), srid=4326
                    )
                return du_lieu

        return FormChiNhanh
    return lop
