from django.templatetags.static import static
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # Trình duyệt luôn thử /favicon.ico; chuyển sang biểu tượng SVG của trang để khỏi báo lỗi 404.
    path("favicon.ico", RedirectView.as_view(url=static("bieu_tuong.svg"), permanent=True)),
    path("", include("ung_dung.chung.urls")),
    path("", include("ung_dung.tai_khoan.urls")),
    path("", include("ung_dung.danh_muc.urls")),
    path("", include("ung_dung.ban_hang.urls")),
    path("", include("ung_dung.webgis.urls")),
    path("", include("ung_dung.tro_chuyen.urls")),
    path("", include("ung_dung.thong_bao.urls")),
    path("", include("ung_dung.thanh_toan.urls")),
    path("", include("ung_dung.noi_dung.urls")),
    path("quan-ly/kho/", include("ung_dung.kho.urls")),
    path("quan-ly/du-bao/", include("ung_dung.du_bao.urls")),
    path("quan-ly/bao-cao/", include("ung_dung.bao_cao.urls")),
]
