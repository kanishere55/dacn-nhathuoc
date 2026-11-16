from django import forms
from django.contrib.gis.geos import Point

from ung_dung.chung.truong_form import TruongHoTen, TruongPhongPhu, TruongSoDienThoai
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
    "noi_dung_chi_tiet": "Mô tả chi tiết",
    "gioi_thieu": "Giới thiệu chi nhánh",
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
MA_GOI_Y = "Tối đa 32 chữ in hoa, số, gạch ngang hoặc gạch dưới; không trùng mục khác."
# Dòng hướng dẫn ngắn ở đầu từng form danh mục: mục này dùng để làm gì, điều gì cần chú ý.
HUONG_DAN_FORM = {
    "thuoc": (
        "Thông tin thuốc dùng chung cho mọi chi nhánh. Đơn vị cơ sở là đơn vị nhỏ nhất dùng "
        "để bán và đếm kho; chọn đúng ngay từ đầu vì sau khi tạo không đổi được."
    ),
    "quy_doi_bao_goi": (
        "Khai báo cách đóng gói để nhập và bán theo hộp, vỉ. Thuốc và hệ số không đổi được sau "
        "khi tạo; cần cách đóng gói khác thì tạo bao gói mới."
    ),
    "chi_nhanh": (
        "Thông tin hiển thị cho khách và dùng để tìm nhà thuốc gần nhất trên bản đồ. Chỉ ngừng "
        "hoạt động được khi kho đã hết hàng và không còn đơn đang xử lý."
    ),
    "don_vi_tinh": "Đơn vị đếm hàng như viên, gói, chai. Mã ngắn viết hoa, ví dụ VIEN.",
    "nhom_atc": (
        "Nhóm thuốc theo hệ thống phân loại ATC của WHO, dùng cho bản đồ nhiệt tồn kho và dự báo."
    ),
    "nha_cung_cap": "Đơn vị giao hàng cho nhà thuốc; phiếu nhập và phiếu trả hàng gắn với mục này.",
    "nhan_vien": "Hồ sơ nhân sự gắn với tài khoản đăng nhập của quản lý hoặc nhân viên chi nhánh.",
    "danh_muc_san_pham": "Nhóm sản phẩm hiển thị trên website để khách duyệt theo nhu cầu.",
    "khuyen_mai": (
        "Giảm giá theo phần trăm cho một thuốc trong khoảng ngày; mỗi thuốc chỉ có một đợt đang "
        "chạy và không áp cho thuốc kê đơn."
    ),
}
# Lời gợi ý dưới từng ô (theo loại danh mục), cho người không quen nghiệp vụ.
TRO_GIUP = {
    "thuoc": {
        "ma_thuoc": MA_GOI_Y,
        "don_vi_tinh": "Đơn vị nhỏ nhất khi bán và đếm kho, ví dụ viên, gói, chai.",
        "gia_ban": "Giá một đơn vị cơ sở, áp dụng chung toàn chuỗi.",
        "nguong_canh_bao": (
            "Cảnh báo khi lượng còn bán được ở một chi nhánh thấp hơn số này; 0 là không cảnh báo."
        ),
        "la_thuoc_ke_don": (
            "Chỉ bán tại quầy khi có đơn của bác sĩ; không khuyến mãi, không ưu đãi thành viên."
        ),
        "dang_hoat_dong": (
            "Bỏ chọn để ngừng kinh doanh; chỉ ngừng được khi đã hết hàng trong kho và hết đơn "
            "đang xử lý."
        ),
    },
    "chi_nhanh": {
        "ma_chi_nhanh": MA_GOI_Y,
        "dang_hoat_dong": (
            "Bỏ chọn để ngừng hoạt động; chỉ ngừng được khi kho đã hết hàng và không còn đơn "
            "đang xử lý."
        ),
    },
    "quy_doi_bao_goi": {
        "ten_quy_doi_bao_goi": "Ghi như trên bao bì, ví dụ Hộp 10 vỉ x 10 viên.",
        "he_so": "Số đơn vị cơ sở trong một bao gói, ví dụ hộp 100 viên thì ghi 100.",
    },
    "don_vi_tinh": {"ma_don_vi_tinh": MA_GOI_Y},
    "nhom_atc": {"ma_nhom_atc": "Mã ATC chữ in hoa và số, ví dụ N02BE."},
    "nha_cung_cap": {"ma_nha_cung_cap": MA_GOI_Y},
    "nhan_vien": {"ma_nhan_vien": MA_GOI_Y},
    "danh_muc_san_pham": {"ma_danh_muc_san_pham": MA_GOI_Y},
    "khuyen_mai": {
        "ma_khuyen_mai": MA_GOI_Y,
        "phan_tram_giam": "Phần trăm giảm trên giá bán, áp dụng từ ngày bắt đầu đến hết ngày kết thúc.",
    },
}
# Trường cố định sau khi tạo (Q02): khóa ô ngay trên form thay vì để sửa rồi mới báo lỗi.
BAT_BIEN = {"thuoc": ("don_vi_tinh",), "quy_doi_bao_goi": ("thuoc", "he_so")}
GOI_Y_BAT_BIEN = (
    "Không đổi được sau khi tạo, để số liệu kho đã ghi giữ đúng nghĩa. Cần khác thì tạo mục mới."
)
# Cột văn bản được nhập nhiều dòng; cột văn bản khác dùng ô một dòng.
NHIEU_DONG = {"noi_dung_chi_tiet", "gioi_thieu"}
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
            ["mo_ta_ngan", "noi_dung_chi_tiet"],
        ),
    ],
    "chi_nhanh": [
        (
            "Thông tin",
            ["ma_chi_nhanh", "ten_chi_nhanh", "dia_chi", "so_dien_thoai", "dang_hoat_dong"],
        ),
        ("Giờ mở cửa hằng ngày", ["gio_mo_cua", "gio_dong_cua"]),
        ("Vị trí trên bản đồ", ["kinh_do", "vi_do"]),
        ("Nội dung hiển thị cho khách", ["gioi_thieu"]),
    ],
}


class FormDanhMuc(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for ten, truong in list(self.fields.items()):
            if ten == "so_dien_thoai":
                # Số điện thoại Việt Nam thật; nhà cung cấp có thể chỉ có tổng đài 1800/1900.
                self.fields[ten] = TruongSoDienThoai(
                    label=truong.label,
                    required=truong.required,
                    help_text=truong.help_text,
                    loai="hotline" if getattr(self, "loai", "") == "nha_cung_cap" else "dien_thoai",
                )
            elif ten == "ten_nhan_vien":
                self.fields[ten] = TruongHoTen(label=truong.label, help_text=truong.help_text)
            elif ten in NHIEU_DONG:
                # Nội dung dài soạn như văn bản Word, lưu HTML đã làm sạch.
                self.fields[ten] = TruongPhongPhu(
                    label=truong.label, required=False, help_text=truong.help_text
                )
            elif isinstance(truong.widget, forms.Textarea):
                truong.widget = forms.TextInput()
            elif isinstance(truong, forms.DateField):
                truong.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
            elif isinstance(truong, forms.TimeField):
                truong.widget = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
        loai = getattr(self, "loai", "")
        for ten, goi_y in TRO_GIUP.get(loai, {}).items():
            if ten in self.fields and not self.fields[ten].help_text:
                self.fields[ten].help_text = goi_y
        if self.instance.pk:
            for ten in BAT_BIEN.get(loai, ()):
                if ten in self.fields:
                    self.fields[ten].disabled = True
                    self.fields[ten].help_text = GOI_Y_BAT_BIEN

    @property
    def huong_dan(self):
        return HUONG_DAN_FORM.get(getattr(self, "loai", ""), "")

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
            if not data:
                return lam_sach(None, initial)  # báo thiếu tệp
            return [lam_sach(tep, initial) for tep in data]
        return [lam_sach(data, initial)]


class TaiAnhForm(forms.Form):
    # Trang dùng JS giữ danh sách ảnh đã chọn nên ô tệp có thể trống lúc gửi; máy chủ vẫn kiểm bắt buộc.
    use_required_attribute = False
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
            # Tọa độ lấy từ bản đồ (bấm, kéo ghim hoặc tìm địa chỉ); ô ẩn giữ giá trị gửi đi.
            nhom_ban_do = "Vị trí trên bản đồ"
            kinh_do = forms.FloatField(
                label="Kinh độ",
                min_value=102,
                max_value=110,
                widget=forms.HiddenInput,
                error_messages={"required": "Hãy ghim vị trí chi nhánh trên bản đồ."},
            )
            vi_do = forms.FloatField(
                label="Vĩ độ",
                min_value=8,
                max_value=23.5,
                widget=forms.HiddenInput,
                error_messages={"required": "Hãy ghim vị trí chi nhánh trên bản đồ."},
            )

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
