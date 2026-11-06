from django import forms
from django.db.models import Subquery

from .models import DuBaoBayNgay, LanThucNghiem


class KichBanForm(forms.Form):
    du_bao = forms.ModelChoiceField(DuBaoBayNgay.objects.none(), label="Nhóm và kỳ dự báo")
    so_luong_ton = forms.FloatField(min_value=0, label="Tồn giả định")
    so_luong_dang_giu = forms.FloatField(min_value=0, label="Lượng giữ giả định")
    so_luong_du_tru = forms.FloatField(min_value=0, label="Mức dự trữ giả định")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cac_du_bao = (
            DuBaoBayNgay.objects.filter(
                ky_danh_gia="tuong_lai",
                ket_qua_mo_hinh__duoc_chon=True,
                ket_qua_mo_hinh__lan_thuc_nghiem_id=Subquery(
                    LanThucNghiem.objects.order_by("-pk").values("pk")[:1]
                ),
            )
            .select_related("ket_qua_mo_hinh")
            .order_by("ket_qua_mo_hinh__ma_atc_nguon")
        )
        self.fields["du_bao"].queryset = cac_du_bao
        self.fields["du_bao"].label_from_instance = lambda dong: (
            f"{dong.ket_qua_mo_hinh.ma_atc_nguon} · 7 ngày sau {dong.ngay_goc:%d/%m/%Y}"
        )

    def clean(self):
        du_lieu = super().clean()
        if du_lieu.get("so_luong_dang_giu", 0) > du_lieu.get("so_luong_ton", 0):
            self.add_error("so_luong_dang_giu", "Lượng giữ không được vượt tồn giả định.")
        return du_lieu
