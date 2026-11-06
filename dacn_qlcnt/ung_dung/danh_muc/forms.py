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
}


class FormDanhMuc(forms.ModelForm):
    def clean(self):
        du_lieu = super().clean()
        for ten, gia_tri in list(du_lieu.items()):
            if isinstance(gia_tri, str):
                du_lieu[ten] = cat_khoang_trang(gia_tri)
        return du_lieu


def lay_form(loai):
    model = DANH_MUC[loai][0]
    cac_cot = [
        cot.name for cot in model._meta.fields if not cot.primary_key and cot.name != "vi_tri"
    ]
    lop = forms.modelform_factory(model, form=FormDanhMuc, fields=cac_cot, labels=NHAN)
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
