from math import isfinite

from rest_framework import serializers

from ung_dung.danh_muc.models import ChiNhanh, DonViTinh, NhomATC, Thuoc


class NhuCauSerializer(serializers.Serializer):
    id_thuoc = serializers.PrimaryKeyRelatedField(
        queryset=Thuoc.objects.filter(dang_hoat_dong=True), source="thuoc"
    )
    so_luong = serializers.IntegerField(min_value=1, max_value=2147483647)


class TimKiemSerializer(serializers.Serializer):
    kinh_do = serializers.FloatField(min_value=-180, max_value=180)
    vi_do = serializers.FloatField(min_value=-90, max_value=90)
    ban_kinh_met = serializers.IntegerField(min_value=100, max_value=50000)
    cac_thuoc = NhuCauSerializer(many=True, allow_empty=False, max_length=30)

    def validate(self, attrs):
        if not isfinite(attrs["kinh_do"]) or not isfinite(attrs["vi_do"]):
            raise serializers.ValidationError("Tọa độ phải là số hữu hạn.")
        return attrs


class DatGiuSerializer(serializers.Serializer):
    id_chi_nhanh = serializers.PrimaryKeyRelatedField(
        queryset=ChiNhanh.objects.filter(dang_hoat_dong=True), source="chi_nhanh"
    )
    cac_thuoc = NhuCauSerializer(many=True, allow_empty=False, max_length=30)


class NhietSerializer(serializers.Serializer):
    nhom_atc = serializers.PrimaryKeyRelatedField(queryset=NhomATC.objects.all())
    don_vi_tinh = serializers.PrimaryKeyRelatedField(queryset=DonViTinh.objects.all())
