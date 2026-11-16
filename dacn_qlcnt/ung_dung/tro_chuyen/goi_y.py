"""Câu hỏi gợi ý trong khung chat của khách: chọn theo ngữ cảnh, tự ẩn khi khách đã nhắn.

Quy tắc (Q38):
- Đang có thẻ sản phẩm chờ gửi: gợi ý câu hỏi về sản phẩm đó ("thuốc này" có nghĩa nhờ thẻ).
- Đang có thẻ đơn chờ gửi: gợi ý câu hỏi về đơn.
- Không có thẻ: chỉ gợi ý câu chung khi khách chưa gửi tin nào trong cuộc (ví dụ nhà thuốc nhắn
  trước về một đơn); khách đã nhắn rồi thì không hiện nữa.
Gửi xong một tin, trình duyệt ẩn gợi ý ngay (tro_chuyen.js); tải lại trang thì quy tắc trên quyết
định, nên gợi ý không quay lại sau khi đã gửi.
"""

from .models import TinNhan

GOI_Y_VE_THUOC = (
    "Nhà thuốc còn thuốc này không?",
    "Thuốc này dùng cho trẻ em được không?",
    "Uống thuốc trước hay sau ăn?",
    "Tôi đang mang thai, dùng được không?",
)
GOI_Y_VE_DON = (
    "Tôi đến nhận muộn hơn được không?",
    "Tôi nhờ người khác nhận giúp được không?",
    "Tôi muốn thêm hoặc bớt thuốc trong đơn.",
)
GOI_Y_CHUNG = (
    "Tôi cần dược sĩ tư vấn chọn thuốc.",
    "Nhà thuốc mở cửa đến mấy giờ?",
    "Tôi muốn giữ thuốc để nhận tại quầy.",
)


def khach_da_nhan(phong) -> bool:
    return TinNhan.objects.filter(cuoc_tro_chuyen=phong, nguoi_gui_id=phong.khach_hang_id).exists()


def chon_goi_y(phong, the_cho=None) -> tuple[str, ...]:
    """Các câu gợi ý cho cuộc trò chuyện đang mở; tuple rỗng nghĩa là không hiện."""
    if the_cho:
        return GOI_Y_VE_THUOC if the_cho["loai"] == "thuoc" else GOI_Y_VE_DON
    return () if khach_da_nhan(phong) else GOI_Y_CHUNG
