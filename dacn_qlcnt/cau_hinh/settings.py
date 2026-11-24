import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import dotenv_values, load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured("Cần đặt DJANGO_SECRET_KEY trong biến môi trường hoặc .env.")
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [
    muc.strip()
    for muc in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if muc.strip()
]
HIEN_NHAN_DIEN_TRANG = os.environ.get("DJANGO_HIEN_NHAN_DIEN_TRANG", "False").lower() == "true"

INSTALLED_APPS = [
    "daphne",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "rest_framework",
    "channels",
    "ung_dung.chung.apps.ChungConfig",
    "ung_dung.tai_khoan.apps.TaiKhoanConfig",
    "ung_dung.danh_muc.apps.DanhMucConfig",
    "ung_dung.kho.apps.KhoConfig",
    "ung_dung.ban_hang.apps.BanHangConfig",
    "ung_dung.webgis.apps.WebGISConfig",
    "ung_dung.tro_chuyen.apps.TroChuyenConfig",
    "ung_dung.du_bao.apps.DuBaoConfig",
    "ung_dung.bao_cao.apps.BaoCaoConfig",
    "ung_dung.thong_bao.apps.ThongBaoConfig",
    "ung_dung.noi_dung.apps.NoiDungConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "ung_dung.chung.tai_len.KiemTraTaiLen",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "cau_hinh.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "ung_dung.chung.nhan_dien_trang.nhan_dien_trang",
                "ung_dung.chung.dieu_huong.dieu_huong",
                "ung_dung.noi_dung.context_processors.website",
            ],
            "builtins": [
                "ung_dung.chung.templatetags.dinh_dang",
                "ung_dung.chung.templatetags.tai_nguyen",
            ],
        },
    }
]
WSGI_APPLICATION = "cau_hinh.wsgi.application"
ASGI_APPLICATION = "cau_hinh.asgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("POSTGRES_DB", "dacn_nhathuoc_nop"),
        "USER": os.environ.get("POSTGRES_USER", "dacn_ung_dung"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 0,
    }
}
for ten_thu_vien in ("GDAL_LIBRARY_PATH", "GEOS_LIBRARY_PATH"):
    if os.environ.get(ten_thu_vien):
        globals()[ten_thu_vien] = os.environ[ten_thu_vien]

AUTH_USER_MODEL = "tai_khoan.TaiKhoan"
LOGIN_URL = "tai_khoan:dang_nhap"
OSRM_BASE_URL = os.environ.get("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")
OSRM_DI_BO_BASE_URL = os.environ.get(
    "OSRM_DI_BO_BASE_URL", "https://routing.openstreetmap.de/routed-foot"
).rstrip("/")
# Bộ kiểm thử không gọi máy chủ OSRM thật (kết quả mạng thay đổi); test cần quãng đường thì giả lập.
if sys.argv[1:2] == ["test"]:
    OSRM_BASE_URL = ""
NOMINATIM_BASE_URL = os.environ.get(
    "NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org"
).rstrip("/")
# Quy tắc mật khẩu của Django, lời báo tiếng Việt (ung_dung/tai_khoan/mat_khau.py).
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "ung_dung.tai_khoan.mat_khau.KhongGiongThongTinCaNhan",
        "OPTIONS": {"user_attributes": ["ten_dang_nhap", "ho_ten", "email"]},
    },
    {"NAME": "ung_dung.tai_khoan.mat_khau.DoDaiToiThieu"},
    {"NAME": "ung_dung.tai_khoan.mat_khau.KhongQuaPhoBien"},
    {"NAME": "ung_dung.tai_khoan.mat_khau.KhongToanChuSo"},
]
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_HTTPONLY = True
# Cookie không phân biệt cổng nên đặt tên riêng, để khi chạy cạnh một ứng dụng Django khác trên cùng
# máy, đăng nhập ở ứng dụng này không đá phiên hay làm hỏng mã CSRF của ứng dụng kia.
SESSION_COOKIE_NAME = "dacn_nop_phien"
CSRF_COOKIE_NAME = "dacn_nop_csrf"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
# E034 giới hạn tên index 30 ký tự vì Oracle; PostgreSQL cho 63 byte và ten_rang_buoc đã kiểm.
SILENCED_SYSTEM_CHECKS = ["models.E034"]
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE
FILE_UPLOAD_HANDLERS = ["ung_dung.chung.tai_len.TaiLenTrongBoNho"]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                {
                    "address": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
                    "socket_connect_timeout": 5,
                    # Channels Redis chờ lệnh BZPOPMIN tới 5 giây khi phòng chưa có tin.
                    "socket_timeout": 10,
                }
            ]
        },
    }
}
# Tên hiển thị và địa chỉ website dùng trong email; đặt trong .env khi triển khai.
TEN_THUONG_HIEU = os.environ.get("TEN_THUONG_HIEU", "Nhà thuốc")
URL_WEBSITE = os.environ.get("URL_WEBSITE", "http://127.0.0.1:8000").rstrip("/")
# Dịch vụ bản đồ công cộng yêu cầu User-Agent định danh ứng dụng gọi tới.
HTTP_USER_AGENT = f"DACN-QuanLyNhaThuoc/1.0 (+{URL_WEBSITE})"

# Email: thiếu tài khoản SMTP thì in email ra console để chạy thử trên máy cá nhân.
# Khóa EMAIL_* trong .env của project được ưu tiên hơn biến môi trường hệ điều hành: máy chạy
# thử có thể còn biến EMAIL_* của project khác (tài khoản Gmail cũ, mật khẩu ứng dụng đã thu
# hồi) và khi đó mã xác thực không bao giờ tới hộp thư. Kiểm tra bằng `manage.py kiem_tra_email`.
_GIA_TRI_ENV = dotenv_values(BASE_DIR / ".env")


def _cau_hinh_email(ten, mac_dinh=""):
    return (_GIA_TRI_ENV.get(ten) or os.environ.get(ten) or mac_dinh).strip()


EMAIL_HOST = _cau_hinh_email("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(_cau_hinh_email("EMAIL_PORT", "587"))
EMAIL_HOST_USER = _cau_hinh_email("EMAIL_HOST_USER")
# Gmail hiển thị mật khẩu ứng dụng thành 4 nhóm cách nhau; bỏ dấu cách khi dán vào .env.
EMAIL_HOST_PASSWORD = _cau_hinh_email("EMAIL_HOST_PASSWORD").replace(" ", "")
EMAIL_USE_SSL = _cau_hinh_email("EMAIL_USE_SSL", "False").lower() == "true"
EMAIL_USE_TLS = not EMAIL_USE_SSL and _cau_hinh_email("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_TIMEOUT = 20
EMAIL_BACKEND = (
    "ung_dung.thong_bao.smtp.GuiThuSmtp"
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
    else "django.core.mail.backends.console.EmailBackend"
)
# Tên người gửi theo thương hiệu lưu trong CSDL (thong_bao.services.dia_chi_gui), trừ khi .env đặt
# DEFAULT_FROM_EMAIL; không lấy biến môi trường hệ điều hành của project khác.
NGUOI_GUI_CO_DINH = bool((_GIA_TRI_ENV.get("DEFAULT_FROM_EMAIL") or "").strip())
DEFAULT_FROM_EMAIL = (_GIA_TRI_ENV.get("DEFAULT_FROM_EMAIL") or "").strip() or (
    f"{TEN_THUONG_HIEU} <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else "khong-tra-loi@localhost"
)
# Gửi SMTP ở luồng nền sau commit để trang không chờ máy chủ thư.
EMAIL_GUI_NEN = os.environ.get("EMAIL_GUI_NEN", "True").lower() == "true"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
