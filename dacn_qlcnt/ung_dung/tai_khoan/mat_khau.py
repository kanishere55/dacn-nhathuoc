"""Bộ kiểm mật khẩu của Django với thông báo tiếng Việt dễ hiểu.

Bản dịch tiếng Việt có sẵn của Django thiếu câu "mật khẩu quá ngắn" (vẫn hiện tiếng Anh) và dịch
máy các câu còn lại; quy tắc kiểm giữ nguyên của Django, chỉ đổi lời báo.
"""

from django.contrib.auth import password_validation as goc


class DoDaiToiThieu(goc.MinimumLengthValidator):
    def get_error_message(self):
        return f"Mật khẩu quá ngắn: cần ít nhất {self.min_length} ký tự."

    def get_help_text(self):
        return f"Mật khẩu có ít nhất {self.min_length} ký tự."


class KhongGiongThongTinCaNhan(goc.UserAttributeSimilarityValidator):
    def get_error_message(self):
        return "Mật khẩu quá giống tên đăng nhập hoặc thông tin cá nhân. Hãy chọn mật khẩu khác."

    def get_help_text(self):
        return "Mật khẩu không được giống tên đăng nhập, họ tên hay email."


class KhongQuaPhoBien(goc.CommonPasswordValidator):
    def get_error_message(self):
        return "Mật khẩu này quá phổ biến, dễ bị đoán. Hãy chọn mật khẩu khác."

    def get_help_text(self):
        return "Không dùng mật khẩu phổ biến như 12345678 hay password."


class KhongToanChuSo(goc.NumericPasswordValidator):
    def get_error_message(self):
        return "Mật khẩu không được chỉ gồm chữ số. Hãy thêm chữ cái."

    def get_help_text(self):
        return "Mật khẩu không được chỉ gồm chữ số."
