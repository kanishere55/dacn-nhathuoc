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
        "tieu_de": "Đặt giữ trên website, nhận tại nhà thuốc gần bạn",
        "mo_ta": "Chọn chi nhánh còn đủ thuốc, hàng được giữ 24 giờ, trả tiền khi nhận tại quầy.",
        "nhan_nut": "Xem danh mục thuốc",
        "duong_dan": "/thuoc/",
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
        <li>Xem chi nhánh còn đủ thuốc trên bản đồ, chọn chi nhánh gần nhất và xem đường đi.</li>
        <li>Đặt giữ thuốc tại chi nhánh, đến quầy nhận và thanh toán trong 24 giờ.</li>
        <li>Nhắn tin hỏi dược sĩ, theo dõi đơn và tải phiếu bán hàng.</li></ul>
        <h2>Cam kết</h2>
        <p>Thuốc kê đơn chỉ bán tại quầy khi dược sĩ đã kiểm tra đơn của bác sĩ. Mỗi lần bán đều
        ghi rõ lô và hạn dùng của thuốc trên phiếu bán hàng.</p>""",
    ),
    (
        "huong-dan-dat-giu",
        "Hướng dẫn đặt giữ thuốc",
        "Giữ thuốc tại chi nhánh 24 giờ, nhận và thanh toán tại quầy.",
        """<p>Đặt giữ giúp bạn chắc chắn chi nhánh còn đủ thuốc trước khi đến, không phải trả tiền
        trước.</p>
        <h2>Các bước</h2>
        <ol><li>Chọn thuốc vào giỏ hoặc tìm thuốc trên <strong>bản đồ nhà thuốc</strong>.</li>
        <li>Chọn chi nhánh còn đủ toàn bộ thuốc, bấm <strong>Đặt giữ tại nhà thuốc</strong>.</li>
        <li>Đến quầy trong <strong>24 giờ</strong>, đọc mã đơn (có trong email và mục Đơn đặt
        giữ) cho nhân viên.</li>
        <li>Thanh toán bằng tiền mặt hoặc chuyển khoản, nhận thuốc và phiếu bán hàng.</li></ol>
        <h2>Lưu ý</h2>
        <ul><li>Mỗi tài khoản giữ tối đa 3 đơn cùng lúc để khách khác vẫn mua được.</li>
        <li>Đổi ý thì hủy đơn trong trang đơn để nhà thuốc nhả hàng cho người khác.</li>
        <li>Quá 24 giờ chưa nhận, đơn tự hết hạn và hàng được trả lại kệ.</li></ul>
        <blockquote>Đơn có thuốc kê đơn: mang theo đơn thuốc còn hạn của bác sĩ, dược sĩ kiểm tra
        trước khi bán.</blockquote>""",
    ),
    (
        "chinh-sach-bao-mat",
        "Chính sách bảo mật",
        "Dữ liệu chúng tôi thu thập và cách chúng tôi bảo vệ.",
        """<h2>Dữ liệu thu thập</h2>
        <p>Họ tên, email, số điện thoại, lịch sử đơn đặt giữ và tin nhắn với nhà thuốc.</p>
        <h2>Mục đích</h2>
        <p>Giữ hàng và giao đơn tại quầy, gửi email xác nhận và trả lời câu hỏi của bạn.</p>
        <h2>Chia sẻ</h2>
        <p>Chúng tôi không bán dữ liệu. Thông tin chỉ được cung cấp khi cơ quan nhà nước có thẩm
        quyền yêu cầu theo quy định pháp luật.</p>
        <h2>Vị trí và dịch vụ bản đồ</h2>
        <p>Vị trí hiện tại chỉ được dùng khi bạn bấm tìm nhà thuốc gần mình. Khi bạn yêu cầu chỉ
        đường, website gửi tọa độ điểm xuất phát và chi nhánh đến dịch vụ định tuyến OSRM. Máy chủ
        định tuyến có thể lưu yêu cầu trong nhật ký vận hành.</p>
        <h2>Quyền của bạn</h2>
        <p>Bạn xem và sửa thông tin trong mục Tài khoản, đổi email bằng mã xác thực và có thể yêu
        cầu xóa tài khoản theo quy định pháp luật về bảo vệ dữ liệu cá nhân.</p>""",
    ),
    (
        "huong-dan-mua-thuoc-ke-don",
        "Hướng dẫn mua thuốc kê đơn",
        "Đặt giữ trên website, mang đơn của bác sĩ tới quầy trong 24 giờ.",
        """<p>Theo Luật Dược, thuốc kê đơn chỉ bán khi có đơn thuốc hợp lệ và dược sĩ đã kiểm tra
        đơn. Website giúp bạn giữ sẵn thuốc tại chi nhánh.</p>
        <ol><li>Tìm thuốc, bấm <strong>Đặt giữ ngay</strong> và chọn chi nhánh còn hàng.</li>
        <li>Mang <strong>đơn thuốc còn hạn</strong> (đơn giấy hoặc mã đơn thuốc điện tử) tới quầy trong 24 giờ.</li>
        <li>Dược sĩ đối chiếu đơn: đúng người bệnh, thuốc, hàm lượng và liều dùng.</li>
        <li>Thanh toán tại quầy bằng tiền mặt hoặc chuyển khoản, nhận thuốc và phiếu bán hàng.</li></ol>
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
