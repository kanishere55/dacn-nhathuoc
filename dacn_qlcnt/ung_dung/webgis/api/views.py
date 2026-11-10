from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ung_dung.ban_hang.services.dat_hang import dat_giu
from ung_dung.chung.permissions import co_quyen, kiem_tra_vai_tro

from ..selectors import lay_ban_do_nhiet, lay_chi_nhanh_ban_do, tim_chi_nhanh
from ..services.dia_chi import dia_chi_tu_toa_do, tim_dia_chi
from .serializers import (
    ChiNhanhGanSerializer,
    DatGiuSerializer,
    NhietSerializer,
    TimDiaChiSerializer,
    TimKiemSerializer,
    ToaDoSerializer,
)


@api_view(["POST"])
@permission_classes([AllowAny])
def tim_kiem(request):
    form = TimKiemSerializer(data=request.data)
    form.is_valid(raise_exception=True)
    return Response({"ket_qua": tim_chi_nhanh(**form.validated_data)})


@api_view(["GET"])
@permission_classes([AllowAny])
def chi_nhanh_gan(request):
    """Chi nhánh đang hoạt động, sắp theo khoảng cách PostGIS tới vị trí người xem."""
    form = ChiNhanhGanSerializer(data=request.query_params)
    form.is_valid(raise_exception=True)
    du_lieu = form.validated_data
    return Response(
        {
            "ket_qua": lay_chi_nhanh_ban_do(
                du_lieu.get("kinh_do"), du_lieu.get("vi_do"), du_lieu.get("ban_kinh_met") or None
            )
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tao_dat_giu(request):
    kiem_tra_vai_tro(request.user, "khach_hang")
    form = DatGiuSerializer(data=request.data)
    form.is_valid(raise_exception=True)
    try:
        don = dat_giu(
            request.user, form.validated_data["chi_nhanh"], form.validated_data["cac_thuoc"]
        )
    except ValidationError as loi:
        return Response({"loi": loi.messages}, status=400)
    return Response(
        {
            "ma_don_hang": don.ma_don_hang,
            "duong_dan": reverse("ban_hang:khach_don_hang_chi_tiet", args=[don.pk]),
        },
        status=201,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ban_do_nhiet(request):
    if not co_quyen(request.user, "ban_do_nhiet.xem"):
        return Response({"loi": "Bạn không có quyền xem bản đồ nhiệt."}, status=403)
    form = NhietSerializer(data=request.query_params)
    form.is_valid(raise_exception=True)
    return Response({"ket_qua": lay_ban_do_nhiet(request.user, **form.validated_data)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tim_dia_chi_api(request):
    form = TimDiaChiSerializer(data=request.query_params)
    form.is_valid(raise_exception=True)
    try:
        return Response({"ket_qua": tim_dia_chi(form.validated_data["q"])})
    except ValidationError as loi:
        return Response({"loi": loi.messages}, status=503)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dia_chi_tu_toa_do_api(request):
    form = ToaDoSerializer(data=request.query_params)
    form.is_valid(raise_exception=True)
    try:
        return Response({"dia_chi": dia_chi_tu_toa_do(**form.validated_data)})
    except ValidationError as loi:
        return Response({"loi": loi.messages}, status=503)
