from django import forms
from django.forms import formset_factory

from ung_dung.danh_muc.models import ChiNhanh, NhaCungCap, QuyDoiBaoGoi, Thuoc
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from .models import LOAI_XUAT_HUY, LoThuoc, PhieuNhap, TonKho
from .selectors import lay_phieu


class PhieuNhapForm(forms.Form):
    chi_nhanh = forms.ModelChoiceField(ChiNhanh.objects.none(), label="Chi nhánh")
    nha_cung_cap = forms.ModelChoiceField(
        NhaCungCap.objects.filter(dang_hoat_dong=True), label="Nhà cung cấp"
    )
    ghi_chu = forms.CharField(label="Ghi chú", required=False, widget=forms.Textarea)

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chi_nhanh"].queryset = lay_chi_nhanh(nguoi)


class DongThuocForm(forms.Form):
    thuoc = forms.ModelChoiceField(Thuoc.objects.filter(dang_hoat_dong=True), label="Thuốc")
    so_luong = forms.IntegerField(label="Số lượng", min_value=1, max_value=2147483647)
    quy_doi_bao_goi = forms.ModelChoiceField(
        QuyDoiBaoGoi.objects.all(), label="Bao gói (trống = đơn vị cơ sở)", required=False
    )


class DongNhapForm(DongThuocForm):
    ma_lo_thuoc = forms.CharField(label="Mã lô", max_length=150)
    ngay_het_han = forms.DateField(
        label="Ngày hết hạn", widget=forms.DateInput(attrs={"type": "date"})
    )
    don_gia = forms.DecimalField(
        label="Giá nhập / đơn vị cơ sở (VND)", max_digits=14, decimal_places=0, min_value=0
    )


class PhieuDieuChuyenForm(forms.Form):
    chi_nhanh_nguon = forms.ModelChoiceField(ChiNhanh.objects.none(), label="Chi nhánh xuất")
    chi_nhanh_dich = forms.ModelChoiceField(
        ChiNhanh.objects.filter(dang_hoat_dong=True), label="Chi nhánh nhận"
    )
    ghi_chu = forms.CharField(label="Ghi chú", required=False)

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chi_nhanh_nguon"].queryset = lay_chi_nhanh(nguoi)


class PhieuTraForm(forms.Form):
    phieu_nhap = forms.ModelChoiceField(PhieuNhap.objects.none(), label="Phiếu nhập gốc")
    ghi_chu = forms.CharField(label="Ghi chú", required=False)

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phieu_nhap"].queryset = lay_phieu(nguoi, PhieuNhap)


class DongTraForm(forms.Form):
    lo_thuoc = forms.ModelChoiceField(LoThuoc.objects.all(), label="Lô đã nhập")
    so_luong = forms.IntegerField(label="Lượng cơ sở trả", min_value=1)

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lo_thuoc"].queryset = LoThuoc.objects.filter(
            tonkho__chi_nhanh__in=lay_chi_nhanh(nguoi)
        ).distinct()


class PhieuXuatHuyForm(forms.Form):
    chi_nhanh = forms.ModelChoiceField(ChiNhanh.objects.none(), label="Chi nhánh")
    loai_xuat_huy = forms.ChoiceField(choices=LOAI_XUAT_HUY, label="Lý do hủy")
    ghi_chu = forms.CharField(
        label="Tình trạng hàng, số biên bản",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chi_nhanh"].queryset = lay_chi_nhanh(nguoi)


class ChonLoTheoTon(forms.ModelChoiceField):
    def label_from_instance(self, lo):
        return f"{lo.thuoc.ten_thuoc} · lô {lo.ma_lo_thuoc} · HSD {lo.ngay_het_han:%d/%m/%Y}"


class DongXuatHuyForm(forms.Form):
    lo_thuoc = ChonLoTheoTon(LoThuoc.objects.none(), label="Lô cần hủy")
    so_luong = forms.IntegerField(label="Lượng cơ sở hủy", min_value=1, max_value=2147483647)

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lo_thuoc"].queryset = (
            LoThuoc.objects.filter(
                tonkho__chi_nhanh__in=lay_chi_nhanh(nguoi), tonkho__so_luong__gt=0
            )
            .select_related("thuoc")
            .order_by("ngay_het_han", "ma_lo_thuoc")
            .distinct()
        )


class PhieuKiemKeForm(forms.Form):
    chi_nhanh = forms.ModelChoiceField(ChiNhanh.objects.none(), label="Chi nhánh")
    ghi_chu = forms.CharField(label="Ghi chú", required=False)
    da_dem_thuc_te = forms.BooleanField(label="Tôi đã đếm thực tế các lô được nhập bên dưới")

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chi_nhanh"].queryset = lay_chi_nhanh(nguoi)


class DongKiemKeForm(forms.Form):
    ton_kho = forms.ModelChoiceField(TonKho.objects.all(), label="Hàng tồn")
    so_luong_so_sach = forms.IntegerField(
        label="Số dư khi mở form", min_value=0, widget=forms.HiddenInput
    )
    so_luong_thuc_te = forms.IntegerField(label="Số lượng đếm thực tế", min_value=0)

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ton_kho"].queryset = TonKho.objects.filter(
            chi_nhanh__in=lay_chi_nhanh(nguoi)
        ).select_related("lo_thuoc__thuoc", "chi_nhanh")


DongNhapFormSet = formset_factory(
    DongNhapForm,
    extra=1,
    min_num=1,
    validate_min=True,
    max_num=50,
    absolute_max=50,
    validate_max=True,
    can_delete=True,
)
DongThuocFormSet = formset_factory(
    DongThuocForm,
    extra=1,
    min_num=1,
    validate_min=True,
    max_num=50,
    absolute_max=50,
    validate_max=True,
    can_delete=True,
)
DongTraFormSet = formset_factory(
    DongTraForm,
    extra=1,
    min_num=1,
    validate_min=True,
    max_num=50,
    absolute_max=50,
    validate_max=True,
    can_delete=True,
)
DongKiemKeFormSet = formset_factory(
    DongKiemKeForm,
    extra=0,
    min_num=1,
    validate_min=True,
    max_num=200,
    absolute_max=200,
    validate_max=True,
    can_delete=True,
)
DongXuatHuyFormSet = formset_factory(
    DongXuatHuyForm,
    extra=0,
    min_num=1,
    validate_min=True,
    max_num=50,
    absolute_max=50,
    validate_max=True,
    can_delete=True,
)
