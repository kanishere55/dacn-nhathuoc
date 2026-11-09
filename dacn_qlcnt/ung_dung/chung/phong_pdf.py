"""Đăng ký font Be Vietnam Pro cho ReportLab; hóa đơn và chứng từ kho dùng chung."""

from pathlib import Path

from django.conf import settings

THU_MUC_PHONG = Path(settings.BASE_DIR) / "static" / "vendor" / "be_vietnam_pro"
_DA_DANG_KY = False


def dang_ky_phong_pdf():
    global _DA_DANG_KY
    if _DA_DANG_KY:
        return
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for ten, tep in (
        ("BeVietnamPro", "BeVietnamPro-Regular.ttf"),
        ("BeVietnamPro-Dam", "BeVietnamPro-Bold.ttf"),
        ("BeVietnamPro-Vua", "BeVietnamPro-SemiBold.ttf"),
    ):
        pdfmetrics.registerFont(TTFont(ten, str(THU_MUC_PHONG / tep)))
    addMapping("BeVietnamPro", 0, 0, "BeVietnamPro")
    addMapping("BeVietnamPro", 1, 0, "BeVietnamPro-Dam")
    _DA_DANG_KY = True
