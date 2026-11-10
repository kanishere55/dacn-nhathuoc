from django import forms
from django.forms import formset_factory
from django.utils import timezone

from ung_dung.danh_muc.models import ChiNhanh, NhaCungCap, QuyDoiBaoGoi, Thuoc
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from .models import LOAI_XUAT_HUY, LoThuoc, PhieuNhap, TonKho
from .selectors import lay_phieu


def chon_san_chi_nhanh(form, ten_truong, nguoi):
    """Người chỉ thuộc một chi nhánh thì chọn sẵn và ẩn ô; form ghi lại để template hiện tên."""
    truong = form.fields[ten_truong]
    truong.queryset = lay_chi_nhanh(nguoi)
    hai = list(truong.queryset[:2])
    form.chi_nhanh_mac_dinh = hai[0] if len(hai) == 1 else None
    if form.chi_nhanh_mac_dinh:
        form.initial.setdefault(ten_truong, form.chi_nhanh_mac_dinh.pk)
        truong.widget = forms.HiddenInput()


class PhieuNhapForm(forms.Form):
    chi_nhanh = forms.ModelChoiceField(
        ChiNhanh.objects.none(), label="Chi nhánh nhận hàng", empty_label="Chọn chi nhánh"
    )
    nha_cung_cap = forms.ModelChoiceField(
        NhaCungCap.objects.filter(dang_hoat_dong=True),
        label="Nhà cung cấp",
        empty_label="Chọn nhà cung cấp",
    )
    ghi_chu = forms.CharField(
        label="Ghi chú",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 2, "placeholder": "Ví dụ: số hóa đơn của nhà cung cấp"}
        ),
    )

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        chon_san_chi_nhanh(self, "chi_nhanh", nguoi)


class TepNhapExcelForm(forms.Form):
    tep_excel = forms.FileField(
        label="Tệp Excel (.xlsx)",
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            }
        ),
    )

    def clean_tep_excel(self):
        from .nhap_excel import LoiTepExcel, doc_tep_nhap

        tep = self.cleaned_data["tep_excel"]
        if not tep.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Chỉ nhận tệp .xlsx.")
        try:
            cac_dong, cac_loi = doc_tep_nhap(tep)
        except LoiTepExcel as loi:
            raise forms.ValidationError(str(loi)) from None
        if cac_loi:
            raise forms.ValidationError(cac_loi)
        return cac_dong


class DongThuocForm(forms.Form):
    thuoc = forms.ModelChoiceField(
        Thuoc.objects.filter(dang_hoat_dong=True), label="Thuốc", empty_label="Chọn thuốc"
    )
    so_luong = forms.IntegerField(label="Số lượng", min_value=1, max_value=2147483647)
    quy_doi_bao_goi = forms.ModelChoiceField(
        QuyDoiBaoGoi.objects.all(),
        label="Tính theo",
        empty_label="Đơn vị lẻ",
        required=False,
    )


class DongNhapForm(DongThuocForm):
    ma_lo_thuoc = forms.CharField(label="Mã lô", max_length=150)
    ngay_het_han = forms.DateField(
        label="Ngày hết hạn", widget=forms.DateInput(attrs={"type": "date"})
    )
    don_gia = forms.DecimalField(
        label="Giá nhập (đ / đơn vị lẻ)", max_digits=14, decimal_places=0, min_value=0
    )


class PhieuDieuChuyenForm(forms.Form):
    chi_nhanh_nguon = forms.ModelChoiceField(
        ChiNhanh.objects.none(), label="Chuyển từ chi nhánh", empty_label="Chọn chi nhánh"
    )
    chi_nhanh_dich = forms.ModelChoiceField(
        ChiNhanh.objects.filter(dang_hoat_dong=True),
        label="Chuyển đến chi nhánh",
        empty_label="Chọn chi nhánh nhận",
    )
    ghi_chu = forms.CharField(label="Ghi chú", required=False)

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        chon_san_chi_nhanh(self, "chi_nhanh_nguon", nguoi)
        if self.chi_nhanh_mac_dinh:
            self.fields["chi_nhanh_dich"].queryset = ChiNhanh.objects.filter(
                dang_hoat_dong=True
            ).exclude(pk=self.chi_nhanh_mac_dinh.pk)


class ChonLoTheoTon(forms.ModelChoiceField):
    def label_from_instance(self, lo):
        return f"{lo.thuoc.ten_thuoc} · lô {lo.ma_lo_thuoc} · HSD {lo.ngay_het_han:%d/%m/%Y}"


class ChonPhieuNhap(forms.ModelChoiceField):
    def label_from_instance(self, phieu):
        return (
            f"{phieu.ma_phieu_nhap} · {phieu.nha_cung_cap.ten_nha_cung_cap}"
            f" · {timezone.localtime(phieu.thoi_diem_tao):%d/%m/%Y}"
        )


class PhieuTraForm(forms.Form):
    phieu_nhap = ChonPhieuNhap(
        PhieuNhap.objects.none(), label="Trả theo phiếu nhập", empty_label="Chọn phiếu nhập gốc"
    )
    ghi_chu = forms.CharField(label="Lý do trả", required=False)

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phieu_nhap"].queryset = lay_phieu(nguoi, PhieuNhap).select_related(
            "nha_cung_cap"
        )


class DongTraForm(forms.Form):
    lo_thuoc = ChonLoTheoTon(LoThuoc.objects.all(), label="Lô trả", empty_label="Chọn lô")
    so_luong = forms.IntegerField(
        label="Số lượng trả (đơn vị lẻ)", min_value=1, max_value=2147483647
    )

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lo_thuoc"].queryset = (
            LoThuoc.objects.filter(tonkho__chi_nhanh__in=lay_chi_nhanh(nguoi))
            .select_related("thuoc")
            .distinct()
        )


class PhieuXuatHuyForm(forms.Form):
    chi_nhanh = forms.ModelChoiceField(
        ChiNhanh.objects.none(), label="Chi nhánh", empty_label="Chọn chi nhánh"
    )
    loai_xuat_huy = forms.ChoiceField(choices=LOAI_XUAT_HUY, label="Lý do hủy")
    ghi_chu = forms.CharField(
        label="Tình trạng hàng, số biên bản",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        chon_san_chi_nhanh(self, "chi_nhanh", nguoi)


class DongXuatHuyForm(forms.Form):
    lo_thuoc = ChonLoTheoTon(LoThuoc.objects.none(), label="Lô cần hủy", empty_label="Chọn lô")
    so_luong = forms.IntegerField(
        label="Số lượng hủy (đơn vị lẻ)", min_value=1, max_value=2147483647
    )

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
    chi_nhanh = forms.ModelChoiceField(
        ChiNhanh.objects.none(), label="Chi nhánh", widget=forms.HiddenInput
    )
    ghi_chu = forms.CharField(label="Ghi chú", required=False)
    da_dem_thuc_te = forms.BooleanField(label="Tôi đã đếm thực tế các lô có nhập số lượng")

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chi_nhanh"].queryset = lay_chi_nhanh(nguoi)


class ChonTonKho(forms.ModelChoiceField):
    ton_theo_id = None

    def label_from_instance(self, ton):
        lo = ton.lo_thuoc
        return f"{lo.thuoc.ten_thuoc} · lô {lo.ma_lo_thuoc} · HSD {lo.ngay_het_han:%d/%m/%Y}"

    def to_python(self, value):
        if self.ton_theo_id is None or value in self.empty_values:
            return super().to_python(value)
        ton = self.ton_theo_id.get(str(value))
        if ton is None:
            raise forms.ValidationError("Lô này không thuộc kho đã chọn.")
        return ton


class DongKiemKeForm(forms.Form):
    ton_kho = ChonTonKho(TonKho.objects.none(), label="Hàng tồn", widget=forms.HiddenInput)
    so_luong_so_sach = forms.IntegerField(
        label="Số dư khi mở form", min_value=0, max_value=2147483647, widget=forms.HiddenInput
    )
    so_luong_thuc_te = forms.IntegerField(
        label="Số lượng đếm thực tế",
        min_value=0,
        max_value=2147483647,
        required=False,
        widget=forms.NumberInput(attrs={"inputmode": "numeric"}),
    )

    def __init__(self, *args, nguoi, ton_theo_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        truong = self.fields["ton_kho"]
        truong.ton_theo_id = ton_theo_id
        if ton_theo_id is None:
            truong.queryset = TonKho.objects.filter(chi_nhanh__in=lay_chi_nhanh(nguoi))
        if self.prefix:
            self.fields["so_luong_thuc_te"].widget.attrs["aria-labelledby"] = (
                f"{self.prefix}-nhan-so-dem {self.prefix}-nhan-lo"
            )

    @property
    def nhan_lo(self):
        truong = self.fields["ton_kho"]
        ton = (truong.ton_theo_id or {}).get(str(self["ton_kho"].value()))
        return truong.label_from_instance(ton) if ton else "Lô không còn trong kho này"


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
