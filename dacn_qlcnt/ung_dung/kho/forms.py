import re
from uuid import uuid4

from django import forms
from django.forms import formset_factory
from django.utils import timezone

from ung_dung.chung.ten_csdl import MA_NGHIEP_VU
from ung_dung.chung.van_ban import la_mot_dong
from ung_dung.danh_muc.models import ChiNhanh, NhaCungCap, QuyDoiBaoGoi, Thuoc
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from .models import LOAI_XUAT_HUY, LoThuoc, PhieuNhap, TonKho
from .quy_tac import SO_NGAY_CAN_HAN, chuan_hoa_ma_lo, la_can_han, loi_han_dung, so_ngay_con_han
from .selectors import lay_phieu


def truong_khoa_yeu_cau():
    """UUID ẩn cấp mỗi lần mở form; gửi lại cùng form chỉ tạo một phiếu (services/chong_trung)."""
    return forms.UUIDField(widget=forms.HiddenInput, initial=uuid4, required=False)


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
    so_hoa_don_nha_cung_cap = forms.CharField(
        label="Số hóa đơn của nhà cung cấp",
        required=False,
        max_length=64,
        help_text="Ký hiệu và số in trên hóa đơn giao kèm hàng, để đối chiếu khi cần.",
        widget=forms.TextInput(attrs={"placeholder": "Ví dụ: 1C26TAA 0001234"}),
    )
    ghi_chu = forms.CharField(
        label="Ghi chú",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 2, "placeholder": "Ví dụ: hàng giao thiếu 1 thùng, hẹn giao bù"}
        ),
    )
    khoa_yeu_cau = truong_khoa_yeu_cau()

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        chon_san_chi_nhanh(self, "chi_nhanh", nguoi)

    def clean_so_hoa_don_nha_cung_cap(self):
        so_hoa_don = self.cleaned_data["so_hoa_don_nha_cung_cap"]
        if not la_mot_dong(so_hoa_don):
            raise forms.ValidationError("Số hóa đơn chỉ ghi trên một dòng.")
        return so_hoa_don


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


class ChonBaoGoi(forms.ModelChoiceField):
    def label_from_instance(self, quy_doi):
        don_vi = quy_doi.thuoc.don_vi_tinh.ten_don_vi_tinh.lower()
        he_so = f"{quy_doi.he_so:,}".replace(",", ".")
        return f"{quy_doi.ten_quy_doi_bao_goi} (= {he_so} {don_vi})"


class DongThuocForm(forms.Form):
    thuoc = forms.ModelChoiceField(
        Thuoc.objects.filter(dang_hoat_dong=True), label="Thuốc", empty_label="Chọn thuốc"
    )
    so_luong = forms.IntegerField(label="Số lượng", min_value=1, max_value=2147483647)
    quy_doi_bao_goi = ChonBaoGoi(
        QuyDoiBaoGoi.objects.select_related("thuoc__don_vi_tinh").order_by("he_so", "pk"),
        label="Tính theo",
        empty_label="Đơn vị cơ sở",
        required=False,
        error_messages={"invalid_choice": "Bao gói này không thuộc thuốc đã chọn; hãy chọn lại."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ô bao gói chỉ có bao gói của thuốc ở chính dòng này (Q02: hệ số riêng từng thuốc).
        # Dòng chưa chọn thuốc để trống; JS điền lại khi người dùng chọn thuốc.
        ma_thuoc = str(self["thuoc"].value() or "")
        truong = self.fields["quy_doi_bao_goi"]
        truong.queryset = (
            truong.queryset.filter(thuoc_id=ma_thuoc)
            if ma_thuoc.isascii() and ma_thuoc.isdecimal()
            else truong.queryset.none()
        )


class DongNhapForm(DongThuocForm):
    ma_lo_thuoc = forms.CharField(
        label="Mã lô",
        max_length=150,
        widget=forms.TextInput(attrs={"autocapitalize": "characters", "spellcheck": "false"}),
    )
    ngay_het_han = forms.DateField(
        label="Ngày hết hạn", widget=forms.DateInput(attrs={"type": "date"})
    )
    don_gia = forms.DecimalField(
        label="Giá nhập / đơn vị cơ sở (đ)", max_digits=14, decimal_places=0, min_value=0
    )
    nhan_lo_can_han = forms.BooleanField(label="Vẫn nhận lô cận hạn", required=False)

    def clean_ma_lo_thuoc(self):
        ma_lo = chuan_hoa_ma_lo(self.cleaned_data["ma_lo_thuoc"])
        if not re.fullmatch(MA_NGHIEP_VU, ma_lo):
            raise forms.ValidationError(
                "Mã lô gồm tối đa 32 chữ in hoa, số, gạch ngang hoặc gạch dưới."
            )
        return ma_lo

    def clean_ngay_het_han(self):
        ngay = self.cleaned_data["ngay_het_han"]
        loi = loi_han_dung(ngay)
        if loi:
            raise forms.ValidationError(loi)
        return ngay

    def clean(self):
        du_lieu = super().clean()
        ngay = du_lieu.get("ngay_het_han")
        if ngay and la_can_han(ngay) and not du_lieu.get("nhan_lo_can_han"):
            self.add_error(
                "nhan_lo_can_han",
                f"Lô chỉ còn {so_ngay_con_han(ngay)} ngày (dưới {SO_NGAY_CAN_HAN} ngày). "
                "Tick “Vẫn nhận lô cận hạn” nếu đã kiểm tra và đồng ý nhận.",
            )
        return du_lieu


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
    khoa_yeu_cau = truong_khoa_yeu_cau()

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
    khoa_yeu_cau = truong_khoa_yeu_cau()

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phieu_nhap"].queryset = lay_phieu(nguoi, PhieuNhap).select_related(
            "nha_cung_cap"
        )


class DongTraForm(forms.Form):
    lo_thuoc = ChonLoTheoTon(
        LoThuoc.objects.none(),
        label="Lô trả",
        empty_label="Chọn lô",
        error_messages={"invalid_choice": "Lô này không có trong phiếu nhập đã chọn."},
    )
    so_luong = forms.IntegerField(
        label="Số lượng trả (đơn vị cơ sở)", min_value=1, max_value=2147483647
    )

    def __init__(self, *args, nguoi, phieu_nhap=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Chỉ trả được lô thuộc phiếu nhập gốc (Q14–Q16): danh sách lô lọc theo phiếu đã chọn.
        self.fields["lo_thuoc"].queryset = (
            LoThuoc.objects.filter(
                chitietphieunhap__phieu_nhap=phieu_nhap,
                chitietphieunhap__phieu_nhap__chi_nhanh__in=lay_chi_nhanh(nguoi),
            )
            .select_related("thuoc")
            .order_by("thuoc__ten_thuoc", "ngay_het_han", "pk")
            .distinct()
            if phieu_nhap
            else LoThuoc.objects.none()
        )


class PhieuXuatHuyForm(forms.Form):
    chi_nhanh = forms.ModelChoiceField(
        ChiNhanh.objects.none(), label="Chi nhánh", empty_label="Chọn chi nhánh"
    )
    loai_xuat_huy = forms.ChoiceField(choices=LOAI_XUAT_HUY, label="Lý do hủy")
    ghi_chu = forms.CharField(
        label="Tình trạng hàng, số biên bản, số văn bản thu hồi",
        required=False,
        help_text="Bắt buộc khi hủy vì hư hỏng hoặc thu hồi.",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    khoa_yeu_cau = truong_khoa_yeu_cau()

    def __init__(self, *args, nguoi, **kwargs):
        super().__init__(*args, **kwargs)
        chon_san_chi_nhanh(self, "chi_nhanh", nguoi)


class DongXuatHuyForm(forms.Form):
    lo_thuoc = ChonLoTheoTon(LoThuoc.objects.none(), label="Lô cần hủy", empty_label="Chọn lô")
    so_luong = forms.IntegerField(
        label="Số lượng hủy (đơn vị cơ sở)", min_value=1, max_value=2147483647
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
    khoa_yeu_cau = truong_khoa_yeu_cau()

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
    def ton(self):
        return (self.fields["ton_kho"].ton_theo_id or {}).get(str(self["ton_kho"].value()))

    @property
    def nhan_lo(self):
        ton = self.ton
        if ton is None:
            return "Lô không còn trong kho này"
        return self.fields["ton_kho"].label_from_instance(ton)


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
