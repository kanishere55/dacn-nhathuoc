"""Tạo nội dung website mặc định trong CSDL: thông tin cửa hàng, trang chính sách, banner.

Ảnh banner là ảnh CC0 của StockSnap, tải về khi chạy lệnh (kiểm SHA-256) rồi lưu bytea;
không có tệp ảnh nào nằm trong thư mục dự án. Chạy lại không ghi đè nội dung đã sửa.
"""

import hashlib
import urllib.request
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction

from ung_dung.danh_muc.models import ChiNhanh

from ...models import BannerTrangChu, ThongTinCuaHang, TrangNoiDung

NGUON_STOCKSNAP = "https://cdn.stocksnap.io/img-thumbs/960w/{}.jpg"
BANNER = [
    {
        "anh": ("WP1KHDXGOY", "a7cc9c3494a6866fb43ccfb1900dfdd10bcdeee29869b2d4de5f7bae7d1f8dda"),
        "tieu_de": "Giao thuốc tận nhà trong bán kính 15 km",
        "mo_ta": "Dược sĩ soạn đơn tại chi nhánh gần bạn nhất, phí giao từ 15.000 đ.",
        "nhan_nut": "Mua thuốc không kê đơn",
        "duong_dan": "/thuoc/?khong_ke_don=1",
        "mau_nen": "#e4f3ec",
    },
    {
        "anh": ("GKABW8BS4I", "5ddb4d1ac4feebc0375b6217d3f076248e9ca0f58a2ea74025d10b7432404c75"),
        "tieu_de": "Dược sĩ tư vấn trước khi bạn dùng thuốc",
        "mo_ta": "Nhắn tin với chi nhánh để hỏi liều dùng, tương tác thuốc và cách bảo quản.",
        "nhan_nut": "Hỏi dược sĩ",
        "duong_dan": "/tro-chuyen/",
        "mau_nen": "#e6eef9",
    },
    {
        "anh": ("NU5JLD5RMX", "5aacb0edcb028f40d70232d32f0459f468329ba26ad8c2b6856086d9c8de7320"),
        "tieu_de": "Bổ sung vitamin, tăng sức đề kháng",
        "mo_ta": "Vitamin C, D và khoáng chất cho cả gia đình, xem kỹ thành phần trước khi mua.",
        "nhan_nut": "Xem vitamin",
        "duong_dan": "/thuoc/?q=vitamin",
        "mau_nen": "#fdf0dd",
    },
    {
        "anh": ("WTWX4BZ4FD", "f46dd54d52801d4ef1b967102c63060f5ec9733de4a7c9c67bb84835bc942632"),
        "tieu_de": "Có đơn của bác sĩ? Đặt giữ, nhận tại quầy",
        "mo_ta": "Thuốc kê đơn được giữ 24 giờ, dược sĩ kiểm tra đơn trước khi bán.",
        "nhan_nut": "Hướng dẫn mua thuốc kê đơn",
        "duong_dan": "/trang/huong-dan-mua-thuoc-ke-don/",
        "mau_nen": "#efe9f8",
    },
    {
        "anh": ("SHZ91GEEC2", "5cbeff5b4759c7865db3b59c32029a3165e46c86f3ce1cce6d914808884ea036"),
        "tieu_de": "Nhà thuốc gần bạn, còn đủ thuốc bạn cần",
        "mo_ta": "Xem trên bản đồ chi nhánh nào còn hàng, giờ mở cửa và đường đi.",
        "nhan_nut": "Tìm nhà thuốc",
        "duong_dan": "/ban-do/",
        "mau_nen": "#e2f1f4",
    },
]

TRANG = [
    (
        "gioi-thieu",
        "Giới thiệu",
        "Chuỗi nhà thuốc đạt chuẩn GPP tại TP. Hồ Chí Minh.",
        """<p>Chúng tôi là chuỗi nhà thuốc bán lẻ tại TP. Hồ Chí Minh. Mỗi chi nhánh có dược sĩ
        tư vấn, thuốc được bảo quản đúng điều kiện ghi trên nhãn và truy được số lô, hạn dùng.</p>
        <h2>Bạn có thể làm gì trên website</h2>
        <ul><li>Tra cứu thuốc theo tên, hoạt chất, nhóm bệnh.</li>
        <li>Xem chi nhánh còn đủ thuốc trên bản đồ, chọn chi nhánh gần nhất.</li>
        <li>Đặt giao tận nơi thuốc không kê đơn, hoặc đặt giữ để nhận tại quầy trong 24 giờ.</li>
        <li>Nhắn tin hỏi dược sĩ, theo dõi đơn và tải hóa đơn bán lẻ.</li></ul>
        <h2>Cam kết</h2>
        <p>Thuốc kê đơn chỉ bán tại quầy khi dược sĩ đã kiểm tra đơn của bác sĩ. Nhà thuốc nhận lại
        hàng lỗi do nhà thuốc và hoàn tiền theo chính sách đổi trả.</p>""",
    ),
    (
        "chinh-sach-giao-hang",
        "Chính sách giao hàng",
        "Phạm vi, phí giao và thời gian giao thuốc không kê đơn.",
        """<h2>Phạm vi giao</h2>
        <p>Đơn được giao từ chi nhánh còn đủ hàng gần địa chỉ của bạn nhất, trong bán kính
        <strong>15 km</strong> theo đường đi.</p>
        <h2>Phí giao</h2>
        <ul><li>3 km đầu: <strong>15.000 đ</strong>.</li><li>Mỗi km tiếp theo: 5.000 đ (làm tròn lên).</li></ul>
        <p>Phí được tính và hiển thị trước khi bạn đặt đơn.</p>
        <h2>Thời gian</h2>
        <p>Chi nhánh xác nhận đơn trong giờ mở cửa và giao trong ngày. Đơn chưa được xác nhận sau
        24 giờ sẽ tự hủy, tiền đã chuyển được hoàn lại.</p>
        <h2>Thanh toán</h2>
        <p>Thanh toán khi nhận hàng (COD), chuyển khoản qua mã VietQR hoặc ví MoMo. Đơn trả trước
        được giữ hàng 30 phút trong lúc chờ thanh toán.</p>
        <blockquote>Thuốc kê đơn không giao qua website. Vui lòng đặt giữ và mang đơn thuốc tới quầy.</blockquote>""",
    ),
    (
        "chinh-sach-doi-tra",
        "Chính sách đổi trả",
        "Nhận lại thuốc giao sai, hư hỏng hoặc hết hạn trong 7 ngày.",
        """<p>Vì an toàn của người dùng, thuốc đã bán ra chỉ được nhận lại khi lỗi thuộc về nhà thuốc.</p>
        <h2>Trường hợp được trả hàng</h2>
        <ul><li>Giao sai thuốc, sai hàm lượng hoặc sai số lượng.</li>
        <li>Bao bì, vỉ, chai bị rách, vỡ, ẩm khi nhận.</li>
        <li>Thuốc đã hết hạn hoặc còn dưới 1 tháng sử dụng khi giao.</li></ul>
        <h2>Cách gửi yêu cầu</h2>
        <ol><li>Vào <strong>Đơn của tôi</strong>, chọn đơn đã hoàn thành trong vòng 7 ngày.</li>
        <li>Bấm <strong>Yêu cầu trả hàng</strong>, chọn thuốc, lý do và chụp ảnh hộp, vỉ, số lô.</li>
        <li>Nhà thuốc liên hệ nhận lại hàng, kiểm tra và hoàn tiền theo giá bạn đã mua.</li></ol>
        <h2>Không áp dụng</h2>
        <p>Đổi ý sau khi đã nhận, thuốc đã mở dùng, thuốc bảo quản không đúng hướng dẫn. Hàng nhận
        lại không được đưa trở lại quầy bán.</p>""",
    ),
    (
        "chinh-sach-bao-mat",
        "Chính sách bảo mật",
        "Dữ liệu chúng tôi thu thập và cách chúng tôi bảo vệ.",
        """<h2>Dữ liệu thu thập</h2>
        <p>Họ tên, email, số điện thoại, địa chỉ giao hàng, lịch sử đơn và tin nhắn với nhà thuốc.
        Ảnh trả hàng chỉ nhân viên chi nhánh xử lý đơn mới xem được.</p>
        <h2>Mục đích</h2>
        <p>Xử lý đơn, giao hàng, hoàn tiền, gửi email xác nhận và trả lời câu hỏi của bạn.</p>
        <h2>Chia sẻ</h2>
        <p>Chúng tôi không bán dữ liệu. Thông tin chỉ chuyển cho đơn vị giao hàng và cổng thanh toán
        ở mức cần thiết để hoàn tất đơn, hoặc khi cơ quan nhà nước có thẩm quyền yêu cầu.</p>
        <h2>Quyền của bạn</h2>
        <p>Bạn xem và sửa thông tin trong mục Tài khoản, đổi email bằng mã xác thực và có thể yêu
        cầu xóa tài khoản theo quy định pháp luật về bảo vệ dữ liệu cá nhân.</p>""",
    ),
    (
        "huong-dan-mua-thuoc-ke-don",
        "Hướng dẫn mua thuốc kê đơn",
        "Đặt giữ trên website, mang đơn của bác sĩ tới quầy trong 24 giờ.",
        """<p>Theo Luật Dược, thuốc kê đơn chỉ bán khi có đơn thuốc hợp lệ và không bán qua giao hàng
        trực tuyến. Website giúp bạn giữ sẵn thuốc tại chi nhánh.</p>
        <ol><li>Tìm thuốc, bấm <strong>Đặt giữ ngay</strong> và chọn chi nhánh còn hàng.</li>
        <li>Mang <strong>đơn thuốc còn hạn</strong> (đơn giấy hoặc mã đơn thuốc điện tử) tới quầy trong 24 giờ.</li>
        <li>Dược sĩ đối chiếu đơn: đúng người bệnh, thuốc, hàm lượng và liều dùng.</li>
        <li>Thanh toán tại quầy bằng tiền mặt hoặc chuyển khoản, nhận thuốc và hóa đơn.</li></ol>
        <blockquote>Nếu đơn không hợp lệ hoặc liều vượt đơn, dược sĩ sẽ không bán và hướng dẫn bạn
        quay lại bác sĩ.</blockquote>""",
    ),
]


def _gon(html):
    return " ".join(html.split()).replace("> <", "><")


class Command(BaseCommand):
    help = "Tạo thông tin cửa hàng, trang chính sách và banner trang chủ mặc định."

    def add_arguments(self, parser):
        parser.add_argument("--bo-qua-anh", action="store_true", help="Không tải ảnh banner.")

    def handle(self, *args, **options):
        with transaction.atomic():
            self._thong_tin()
            for thu_tu, (duong_dan, tieu_de, tom_tat, noi_dung) in enumerate(TRANG):
                _, tao = TrangNoiDung.objects.get_or_create(
                    duong_dan_trang=duong_dan,
                    defaults={
                        "tieu_de": tieu_de,
                        "tom_tat": tom_tat,
                        "noi_dung_trang": _gon(noi_dung),
                        "thu_tu": thu_tu,
                    },
                )
                self.stdout.write(f"{'Tạo' if tao else 'Giữ'} trang {duong_dan}")
        if options["bo_qua_anh"] or BannerTrangChu.objects.exists():
            self.stdout.write("Bỏ qua banner (đã có hoặc không tải ảnh).")
            return
        for thu_tu, muc in enumerate(BANNER):
            ma_anh, ma_bam = muc["anh"]
            du_lieu = self._tai(NGUON_STOCKSNAP.format(ma_anh), ma_bam)
            banner = BannerTrangChu(
                **{k: v for k, v in muc.items() if k != "anh"},
                nguon_anh=f"StockSnap {ma_anh}, giấy phép CC0",
                thu_tu=thu_tu,
            )
            banner.gan_du_lieu(SimpleUploadedFile(f"{ma_anh}.jpg", du_lieu, "image/jpeg"))
            banner.save()
            self.stdout.write(f"Tạo banner {muc['tieu_de']}")

    def _thong_tin(self):
        if ThongTinCuaHang.objects.exists():
            return
        chi_nhanh = ChiNhanh.objects.filter(dang_hoat_dong=True).order_by("pk").first()
        ThongTinCuaHang.objects.create(
            ten_thuong_hieu="Nhà thuốc Tâm An"
            if settings.TEN_THUONG_HIEU == "Nhà thuốc"
            else settings.TEN_THUONG_HIEU,
            khau_hieu="Chuỗi nhà thuốc GPP tại TP.HCM",
            hotline=(
                chi_nhanh.so_dien_thoai if chi_nhanh and chi_nhanh.so_dien_thoai else "02839000000"
            ),
            email_lien_he=(settings.EMAIL_HOST_USER or "lienhe@example.com").lower(),
            dia_chi_tru_so=chi_nhanh.dia_chi if chi_nhanh else "TP. Hồ Chí Minh",
            gio_lam_viec="07:00–22:00 hằng ngày",
        )
        self.stdout.write("Tạo thông tin cửa hàng")

    def _tai(self, url, ma_bam):
        yeu_cau = urllib.request.Request(url, headers={"User-Agent": settings.HTTP_USER_AGENT})
        with urllib.request.urlopen(yeu_cau, timeout=30) as phan_hoi:
            du_lieu = phan_hoi.read()
        if hashlib.sha256(du_lieu).hexdigest() != ma_bam:
            raise ValueError(f"Ảnh tải về không khớp mã băm: {url}")
        return BytesIO(du_lieu).getvalue()
