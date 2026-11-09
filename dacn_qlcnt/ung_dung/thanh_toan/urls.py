from django.urls import path

from .views import cong, khach

app_name = "thanh_toan"
urlpatterns = [
    path("don-hang/<int:ma>/thanh-toan/", khach.trang_thanh_toan, name="trang_thanh_toan"),
    path("don-hang/<int:ma>/thanh-toan/trang-thai/", khach.trang_thai, name="trang_thai"),
    path("don-hang/<int:ma>/thanh-toan/vietqr.png", khach.anh_qr, name="anh_qr"),
    path("don-hang/<int:ma>/thanh-toan/momo/", khach.bat_dau_momo, name="bat_dau_momo"),
    path("thanh-toan/momo/quay-ve/", khach.momo_quay_ve, name="momo_quay_ve"),
    path("thanh-toan/momo/ipn/", cong.momo_ipn, name="momo_ipn"),
    path("thanh-toan/sepay/webhook/", cong.sepay_webhook, name="sepay_webhook"),
]
