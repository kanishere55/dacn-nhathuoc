"""Thông báo lỗi tiếng Việt dễ hiểu cho toàn hệ thống.

Bản dịch tiếng Việt kèm Django/DRF còn sót câu tiếng Anh (ràng buộc model, mật khẩu, API) và
nhiều câu dịch máy khó hiểu ("Nhập một số tổng thể", "Đảm bảo giá trị này là nhỏ hơn hoặc bằng
với 5 ."). Hàm `ap_dung()` được gọi một lần khi khởi động (ChungConfig.ready) để thay lời báo
mặc định của các trường form, bộ kiểm (validator), ràng buộc model và lỗi API; quy tắc kiểm giữ
nguyên. Form nào khai báo error_messages riêng vẫn dùng lời riêng đó.

Cảnh báo của trình duyệt (ô bắt buộc, sai kiểu email/số...) do chung/js/kiem_tra_form.js đổi sang
tiếng Việt.
"""

from django import forms
from django.core import validators
from django.db import models
from django.db.models.constraints import BaseConstraint

BAT_BUOC = "Vui lòng nhập thông tin này."
CHON_BAT_BUOC = "Vui lòng chọn một mục."

LOI_TRUONG_FORM = {
    forms.Field: {"required": BAT_BUOC},
    forms.CharField: {},
    forms.IntegerField: {"invalid": "Vui lòng nhập số nguyên, ví dụ 12."},
    forms.FloatField: {"invalid": "Vui lòng nhập một số, ví dụ 12,5."},
    forms.DecimalField: {"invalid": "Vui lòng nhập một số, ví dụ 12500."},
    forms.DateField: {
        "invalid": "Ngày chưa đúng. Hãy chọn ngày trên lịch hoặc nhập ngày/tháng/năm."
    },
    forms.TimeField: {"invalid": "Giờ chưa đúng. Hãy nhập giờ:phút, ví dụ 07:30."},
    forms.DateTimeField: {"invalid": "Thời điểm chưa đúng. Hãy nhập ngày và giờ hợp lệ."},
    forms.DurationField: {"invalid": "Khoảng thời gian chưa đúng."},
    forms.EmailField: {},
    forms.URLField: {},
    forms.BooleanField: {"required": "Vui lòng đánh dấu ô này để tiếp tục."},
    forms.ChoiceField: {
        "required": CHON_BAT_BUOC,
        "invalid_choice": "Lựa chọn không hợp lệ. Vui lòng chọn lại trong danh sách.",
    },
    forms.TypedChoiceField: {},
    forms.MultipleChoiceField: {
        "required": "Vui lòng chọn ít nhất một mục.",
        "invalid_choice": "Có mục đã chọn không hợp lệ. Vui lòng chọn lại.",
        "invalid_list": "Danh sách lựa chọn không hợp lệ.",
    },
    forms.ModelChoiceField: {
        "required": CHON_BAT_BUOC,
        "invalid_choice": "Mục đã chọn không còn tồn tại hoặc không được phép. Vui lòng chọn lại.",
    },
    forms.ModelMultipleChoiceField: {
        "required": "Vui lòng chọn ít nhất một mục.",
        "invalid_choice": "Có mục đã chọn không còn tồn tại. Vui lòng chọn lại.",
        "invalid_pk_value": "Có mục đã chọn không hợp lệ.",
        "invalid_list": "Danh sách lựa chọn không hợp lệ.",
    },
    forms.UUIDField: {"invalid": "Mã không hợp lệ. Hãy tải lại trang rồi thử lại."},
    forms.FileField: {
        "required": "Vui lòng chọn tệp.",
        "invalid": "Không đọc được tệp gửi lên. Hãy chọn lại tệp.",
        "missing": "Chưa nhận được tệp. Hãy chọn lại tệp.",
        "empty": "Tệp đã chọn rỗng (0 byte).",
        "max_length": "Tên tệp quá dài (tối đa %(max)d ký tự, tệp này %(length)d ký tự).",
        "contradiction": "Hãy chọn tệp mới hoặc đánh dấu xóa, không làm cả hai.",
    },
    forms.ImageField: {
        "invalid_image": "Tệp không phải ảnh hợp lệ. Chỉ nhận ảnh JPEG, PNG, WebP hoặc GIF.",
    },
    forms.JSONField: {"invalid": "Dữ liệu JSON không hợp lệ."},
}

LOI_BO_KIEM = {
    validators.MaxLengthValidator: "Tối đa %(limit_value)d ký tự (bạn đã nhập %(show_value)d).",
    validators.MinLengthValidator: "Cần ít nhất %(limit_value)d ký tự (bạn đã nhập %(show_value)d).",
    validators.MaxValueValidator: "Giá trị tối đa là %(limit_value)s.",
    validators.MinValueValidator: "Giá trị tối thiểu là %(limit_value)s.",
    validators.StepValueValidator: "Giá trị phải là bội số của %(limit_value)s.",
    validators.EmailValidator: "Email chưa đúng định dạng. Ví dụ đúng: ten.ban@gmail.com.",
    validators.URLValidator: "Đường dẫn chưa đúng, ví dụ https://nhathuoc.vn/trang.",
    validators.ProhibitNullCharactersValidator: "Nội dung chứa ký tự không hợp lệ.",
    validators.FileExtensionValidator: (
        "Đuôi tệp “%(extension)s” không được nhận. Chỉ nhận: %(allowed_extensions)s."
    ),
}

LOI_THAP_PHAN = {
    "invalid": "Vui lòng nhập một số.",
    "max_digits": "Số quá lớn: tối đa %(max)s chữ số.",
    "max_decimal_places": "Tối đa %(max)s chữ số sau dấu phẩy.",
    "max_whole_digits": "Phần nguyên tối đa %(max)s chữ số.",
}

LOI_TRUONG_MODEL = {
    "invalid_choice": "Giá trị đã chọn không hợp lệ.",
    "null": BAT_BUOC,
    "blank": BAT_BUOC,
    "unique": "%(field_label)s này đã được dùng. Vui lòng nhập giá trị khác.",
    "unique_for_date": "%(field_label)s đã được dùng trong cùng %(lookup_type)s.",
}

LOI_KIEU_MODEL = {
    models.IntegerField: "“%(value)s” không phải số nguyên.",
    models.FloatField: "“%(value)s” không phải là số.",
    models.DecimalField: "“%(value)s” không phải là số.",
    models.DateField: "“%(value)s” không phải ngày hợp lệ (năm-tháng-ngày).",
    models.TimeField: "“%(value)s” không phải giờ hợp lệ (giờ:phút).",
    models.DateTimeField: "“%(value)s” không phải thời điểm hợp lệ.",
    models.BooleanField: "“%(value)s” phải là đúng hoặc sai.",
    models.UUIDField: "“%(value)s” không phải mã UUID hợp lệ.",
    models.JSONField: "Dữ liệu JSON không hợp lệ.",
}

# Lời chung khi dữ liệu vi phạm một ràng buộc model chưa khai báo lời riêng (không lộ tên kỹ thuật).
LOI_RANG_BUOC = (
    "Dữ liệu chưa hợp lệ hoặc trùng với dữ liệu đã có. Vui lòng kiểm tra lại các ô đã nhập."
)


def _loi_trung_nhieu_cot(self, model_class, unique_check):
    """Thay cho Model.unique_error_message: không dùng verbose_name dài của bảng."""
    from django.core.exceptions import ValidationError

    if len(unique_check) == 1:
        truong = model_class._meta.get_field(unique_check[0])
        return ValidationError(
            message=LOI_TRUONG_MODEL["unique"],
            code="unique",
            params={"field_label": str(truong.verbose_name).capitalize()},
        )
    nhan = ", ".join(
        str(model_class._meta.get_field(ten).verbose_name).lower() for ten in unique_check
    )
    return ValidationError(
        message=f"Đã có dữ liệu trùng {nhan}. Vui lòng nhập giá trị khác.",
        code="unique_together",
    )


def _ap_dung_drf():
    try:
        from rest_framework import exceptions, fields
    except ImportError:
        return
    exceptions.NotAuthenticated.default_detail = "Bạn cần đăng nhập để dùng chức năng này."
    exceptions.AuthenticationFailed.default_detail = "Thông tin đăng nhập không đúng."
    exceptions.PermissionDenied.default_detail = "Bạn không có quyền thực hiện thao tác này."
    exceptions.NotFound.default_detail = "Không tìm thấy dữ liệu."
    exceptions.ParseError.default_detail = "Yêu cầu gửi lên sai định dạng."
    exceptions.Throttled.default_detail = "Bạn thao tác quá nhanh. Vui lòng thử lại sau ít phút."
    exceptions.ValidationError.default_detail = "Dữ liệu gửi lên không hợp lệ."
    exceptions.MethodNotAllowed.default_detail = "Phương thức “{method}” không được hỗ trợ."
    fields.Field.default_error_messages.update({"required": BAT_BUOC, "null": BAT_BUOC})
    fields.IntegerField.default_error_messages["invalid"] = "Vui lòng nhập số nguyên."
    fields.FloatField.default_error_messages["invalid"] = "Vui lòng nhập một số."
    fields.DecimalField.default_error_messages["invalid"] = "Vui lòng nhập một số."
    fields.CharField.default_error_messages["blank"] = BAT_BUOC


def _doi_loi_rang_buoc():
    """Ràng buộc không khai lời riêng thì báo lời chung tiếng Việt.

    Chỉ đổi lúc lấy lời báo, không đổi default_violation_error_message: giá trị đó nằm trong
    deconstruct() của ràng buộc, đổi đi thì makemigrations tưởng mọi ràng buộc đã thay đổi.
    """
    mac_dinh = BaseConstraint.default_violation_error_message
    lay_goc = BaseConstraint.get_violation_error_message

    def get_violation_error_message(self):
        if str(self.violation_error_message) == str(mac_dinh):
            return LOI_RANG_BUOC
        return lay_goc(self)

    BaseConstraint.get_violation_error_message = get_violation_error_message


def _gan_loi(lop, loi):
    """Chỉ sửa từ điển lời báo của chính lớp; lớp kế thừa từ điển của lớp cha thì tạo từ điển
    riêng, để đổi lời của BooleanField không làm đổi lời "bắt buộc" của mọi trường."""
    if "default_error_messages" in lop.__dict__:
        lop.default_error_messages.update(loi)
    elif loi:
        lop.default_error_messages = dict(loi)


def ap_dung():
    for lop, loi in LOI_TRUONG_FORM.items():
        _gan_loi(lop, loi)
    for lop, loi in LOI_KIEU_MODEL.items():
        _gan_loi(lop, {"invalid": loi})
    for lop, loi in LOI_BO_KIEM.items():
        lop.message = loi
    validators.DecimalValidator.messages.update(LOI_THAP_PHAN)
    models.Field.default_error_messages.update(LOI_TRUONG_MODEL)
    _doi_loi_rang_buoc()
    models.Model.unique_error_message = _loi_trung_nhieu_cot
    _ap_dung_drf()
