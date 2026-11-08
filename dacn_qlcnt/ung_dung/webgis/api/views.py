from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ung_dung.ban_hang.services.dat_giu import dat_giu
from ung_dung.chung.permissions import kiem_tra_vai_tro, la_quan_tri

from ..selectors import lay_ban_do_nhiet, tim_chi_nhanh
from .serializers import DatGiuSerializer, NhietSerializer, TimKiemSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def tim_kiem(request):
    form = TimKiemSerializer(data=request.data)
    form.is_valid(raise_exception=True)
    return Response({"ket_qua": tim_chi_nhanh(**form.validated_data)})


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
            "ma_don_dat_giu": don.ma_don_dat_giu,
            "duong_dan": reverse("ban_hang:khach_don_dat_giu_chi_tiet", args=[don.pk]),
        },
        status=201,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ban_do_nhiet(request):
    if not la_quan_tri(request.user):
        return Response({"loi": "Bạn không có quyền xem bản đồ nhiệt."}, status=403)
    form = NhietSerializer(data=request.query_params)
    form.is_valid(raise_exception=True)
    return Response({"ket_qua": lay_ban_do_nhiet(request.user, **form.validated_data)})
