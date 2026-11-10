"""Backend SMTP báo đúng nguyên nhân khi Gmail từ chối đăng nhập, và giải thích lỗi bằng tiếng Việt.

smtplib mặc định thử lần lượt nhiều kiểu AUTH; Gmail trả 535 (sai tài khoản/mật khẩu ứng dụng)
rồi ngắt kết nối ở lần thử sau, nên lỗi cuối cùng chỉ còn "Connection unexpectedly closed" và che
mất nguyên nhân thật. Ở đây chỉ dùng AUTH PLAIN (Gmail hỗ trợ) để giữ nguyên mã 535.
"""

import smtplib
import socket
import ssl

from django.core.mail.backends.smtp import EmailBackend


class _ChiAuthPlain:
    def login(self, user, password, *, initial_response_ok=True):
        self.ehlo_or_helo_if_needed()
        if not self.has_extn("auth"):
            raise smtplib.SMTPNotSupportedError("Máy chủ thư không hỗ trợ đăng nhập (AUTH).")
        self.user, self.password = user, password
        return self.auth("PLAIN", self.auth_plain, initial_response_ok=initial_response_ok)


class _SMTP(_ChiAuthPlain, smtplib.SMTP):
    pass


class _SMTPSSL(_ChiAuthPlain, smtplib.SMTP_SSL):
    pass


class GuiThuSmtp(EmailBackend):
    @property
    def connection_class(self):
        return _SMTPSSL if self.use_ssl else _SMTP


def giai_thich_loi(loi):
    """Câu tiếng Việt cho nhật ký email: người quản trị biết phải sửa gì."""
    if isinstance(loi, smtplib.SMTPAuthenticationError):
        return (
            "Gmail từ chối đăng nhập (mã 535): sai địa chỉ gửi hoặc mật khẩu ứng dụng đã bị đổi/thu "
            "hồi. Tạo mật khẩu ứng dụng mới rồi điền EMAIL_HOST_USER, EMAIL_HOST_PASSWORD trong .env."
        )
    if isinstance(loi, smtplib.SMTPRecipientsRefused):
        return "Máy chủ thư từ chối địa chỉ nhận. Kiểm tra lại email người nhận."
    if isinstance(loi, smtplib.SMTPSenderRefused):
        return "Máy chủ thư từ chối địa chỉ gửi. Địa chỉ gửi phải trùng tài khoản Gmail đăng nhập."
    if isinstance(loi, smtplib.SMTPServerDisconnected):
        return "Máy chủ thư ngắt kết nối giữa chừng. Kiểm tra cổng, TLS/SSL và tài khoản gửi."
    if isinstance(loi, ssl.SSLError):
        return "Lỗi mã hóa TLS/SSL với máy chủ thư. Cổng 587 dùng TLS, cổng 465 dùng SSL."
    if isinstance(loi, (socket.timeout, TimeoutError)):
        return "Quá thời gian chờ máy chủ thư. Kiểm tra mạng hoặc tường lửa."
    if isinstance(loi, (socket.gaierror, ConnectionError, OSError)):
        return "Không kết nối được máy chủ thư. Kiểm tra mạng, EMAIL_HOST và EMAIL_PORT."
    return "Gửi email lỗi không rõ nguyên nhân."
