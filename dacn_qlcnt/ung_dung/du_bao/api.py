"""API dữ liệu biểu đồ dự báo theo nhóm ATC; trang kết quả gọi bằng Fetch khi đổi nhóm."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ung_dung.chung.permissions import co_quyen

from .selectors import lan_moi_nhat, lay_chi_tiet_nhom


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chi_tiet_nhom(request, ma_atc):
    if not co_quyen(request.user, "du_bao.xem"):
        return Response({"loi": "Bạn không có quyền xem dự báo."}, status=403)
    lan = lan_moi_nhat()
    du_lieu = lay_chi_tiet_nhom(lan, ma_atc) if lan else None
    if du_lieu is None:
        return Response({"loi": "Không có kết quả cho nhóm ATC này."}, status=404)
    return Response(du_lieu)
