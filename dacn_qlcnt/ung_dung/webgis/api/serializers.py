from math import isfinite

from rest_framework import serializers

from ung_dung.ban_hang.gio_hang import SO_LUONG_TOI_DA, SO_THUOC_TOI_DA
from ung_dung.danh_muc.models import ChiNhanh, DonViTinh, NhomATC, Thuoc


class NhuCauSerializer(serializers.Serializer):
    id_thuoc = serializers.PrimaryKeyRelatedField(
        queryset=Thuoc.objects.filter(dang_hoat_dong=True), source="thuoc"
    )
    so_luong = serializers.IntegerField(min_value=1, max_value=SO_LUONG_TOI_DA)


class TimKiemSerializer(serializers.Serializer):
    kinh_do = serializers.FloatField(min_value=-180, max_value=180)
    vi_do = serializers.FloatField(min_value=-90, max_value=90)
    ban_kinh_met = serializers.IntegerField(min_value=100, max_value=50000)
    cac_thuoc = NhuCauSerializer(many=True, allow_empty=False, max_length=SO_THUOC_TOI_DA)

    def validate(self, attrs):
        if not isfinite(attrs["kinh_do"]) or not isfinite(attrs["vi_do"]):
            raise serializers.ValidationError("Tọa độ phải là số hữu hạn.")
        return attrs


class DatGiuSerializer(serializers.Serializer):
    id_chi_nhanh = serializers.PrimaryKeyRelatedField(
        queryset=ChiNhanh.objects.filter(dang_hoat_dong=True), source="chi_nhanh"
    )
    cac_thuoc = NhuCauSerializer(many=True, allow_empty=False, max_length=SO_THUOC_TOI_DA)


class ChiNhanhGanSerializer(serializers.Serializer):
    kinh_do = serializers.FloatField(min_value=-180, max_value=180, required=False)
    vi_do = serializers.FloatField(min_value=-90, max_value=90, required=False)
    ban_kinh_met = serializers.IntegerField(
        min_value=0, max_value=200000, required=False, default=0
    )

    def validate(self, du_lieu):
        if ("kinh_do" in du_lieu) != ("vi_do" in du_lieu):
            raise serializers.ValidationError("Cần đủ cả kinh độ và vĩ độ.")
        return du_lieu


class NhietSerializer(serializers.Serializer):
    nhom_atc = serializers.PrimaryKeyRelatedField(queryset=NhomATC.objects.all())
    don_vi_tinh = serializers.PrimaryKeyRelatedField(queryset=DonViTinh.objects.all())


class TimDiaChiSerializer(serializers.Serializer):
    q = serializers.CharField(min_length=3, max_length=200, trim_whitespace=True)


class ToaDoSerializer(serializers.Serializer):
    vi_do = serializers.FloatField(min_value=8.0, max_value=23.5)
    kinh_do = serializers.FloatField(min_value=102.0, max_value=110.0)
