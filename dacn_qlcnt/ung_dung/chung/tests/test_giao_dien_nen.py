"""Nền tảng giao diện: token màu, thứ tự cascade CSS, khung hai khu, thông báo, trang lỗi, menu."""

import re
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.storage.base import Message
from django.contrib.messages.storage.cookie import CookieStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import path, resolve, reverse

from ung_dung.chung.dieu_huong import CAC_NHOM, NHOM_THU_GON, QUYEN_MENU
from ung_dung.chung.permissions import co_quyen
from ung_dung.kho.tests.du_lieu import tao_du_lieu

CSS = Path(settings.BASE_DIR, "static", "css")
JS_GIAO_DIEN = Path(settings.BASE_DIR, "ung_dung", "chung", "static", "chung", "js", "giao_dien.js")


def _do_choi(ma_hex):
    gia_tri = [int(ma_hex.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    tuyen_tinh = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in gia_tri]
    return 0.2126 * tuyen_tinh[0] + 0.7152 * tuyen_tinh[1] + 0.0722 * tuyen_tinh[2]


def tuong_phan(mau_a, mau_b):
    sang, toi = sorted((_do_choi(mau_a), _do_choi(mau_b)), reverse=True)
    return (sang + 0.05) / (toi + 0.05)


def _khoi_theme():
    nguon = (CSS / "giao_dien.css").read_text(encoding="utf-8")
    bat_dau = nguon.index("@theme static {")
    return nguon, bat_dau, nguon.index("\n}", bat_dau)


def _vi_tri_khoi(chuoi, bat_dau):
    """Vị trí đóng ngoặc của khối bắt đầu tại `bat_dau` (đếm cặp ngoặc nhọn)."""
    sau = 0
    for i in range(chuoi.index("{", bat_dau), len(chuoi)):
        sau += {"{": 1, "}": -1}.get(chuoi[i], 0)
        if sau == 0:
            return i
    raise AssertionError("Khối CSS không đóng.")


class TokenThietKeTests(SimpleTestCase):
    def test_cap_mau_token_dat_tuong_phan_wcag_aa(self):
        nguon, bat_dau, ket_thuc = _khoi_theme()
        mau = dict(re.findall(r"--color-([a-z-]+):\s*(#[0-9a-f]{6})", nguon[bat_dau:ket_thuc]))
        mau["trang"] = "#ffffff"
        cac_cap = [
            ("chu", "nen", 7),
            ("chu-phu", "nen", 4.5),
            ("chu-phu", "be-mat", 4.5),
            ("chu-phu", "nen-dam", 4.5),
            ("chu-nhat", "be-mat", 4.5),
            ("chinh", "be-mat", 4.5),
            ("trang", "chinh", 4.5),
            ("chinh-dam", "chinh-nhat", 4.5),
            ("chinh-dam", "chinh-nhat-dam", 4.5),
            ("trang", "loi-dam", 4.5),
            ("trang", "nhan", 4.5),
            ("thanh-cong", "thanh-cong-nen", 4.5),
            ("canh-bao", "canh-bao-nen", 4.5),
            ("loi", "loi-nen", 4.5),
            ("thong-tin", "thong-tin-nen", 4.5),
            ("chu-tren-toi", "chinh-sau", 4.5),
            ("chu-tren-toi-phu", "chinh-sau", 4.5),
            # Viền ô nhập là thành phần giao diện: tối thiểu 3:1 (WCAG 2.2 SC 1.4.11).
            ("vien-o-nhap", "be-mat", 3),
        ]
        for chu, nen, toi_thieu in cac_cap:
            with self.subTest(chu=chu, nen=nen):
                self.assertGreaterEqual(tuong_phan(mau[chu], mau[nen]), toi_thieu)

    def test_tep_khung_khong_viet_cung_ma_mau(self):
        """Màu chỉ khai báo ở @theme; các tệp khung dùng var(--…) (F09, QT-14)."""
        nguon, bat_dau, ket_thuc = _khoi_theme()
        ngoai_theme = nguon[:bat_dau] + nguon[ket_thuc:]
        ngoai_theme = re.sub(r"/\*.*?\*/", "", ngoai_theme, flags=re.S)
        self.assertEqual(set(re.findall(r"#[0-9a-fA-F]{3,8}\b", ngoai_theme)) - {"#fff"}, set())
        for ten in ("khach.css", "quan_ly.css"):
            with self.subTest(tep=ten):
                ma = re.findall(r"#[0-9a-fA-F]{3,8}\b", (CSS / ten).read_text(encoding="utf-8"))
                self.assertEqual(set(ma) - {"#fff"}, set())

    def test_lop_bo_nghia_cua_tep_mien_thang_lop_nen(self):
        """MISS-01/CB-01: quy tắc nền nằm trong lớp con components.nen nên lớp của tệp miền luôn thắng."""
        bien_dich = (CSS / "da_bien_dich.css").read_text(encoding="utf-8")
        dau_nen = bien_dich.index("@layer nen{")
        cuoi_nen = _vi_tri_khoi(bien_dich, dau_nen)
        dau_components = bien_dich.index("@layer components{")
        self.assertLess(dau_components, dau_nen)
        self.assertLess(cuoi_nen, _vi_tri_khoi(bien_dich, dau_components))

        def vi_tri(lop):
            return [
                m.start() for m in re.finditer(r"(?<=[{}])\." + re.escape(lop) + r"\{", bien_dich)
            ]

        for lop in ("nut", "thong-bao", "thong-bao-loi", "khoi-trang", "nhan-trang-thai"):
            with self.subTest(lop=lop):
                self.assertTrue(vi_tri(lop))
                self.assertTrue(all(dau_nen < p < cuoi_nen for p in vi_tri(lop)))
        # Lớp bổ nghĩa ở tệp miền (nút MoMo) nằm ngoài lớp nền.
        self.assertTrue(all(not dau_nen < p < cuoi_nen for p in vi_tri("nut-momo")))
        self.assertGreater(vi_tri("thong-bao-loi")[0], vi_tri("thong-bao")[0])
        self.assertNotIn(".thong-bao-loi", (CSS / "khach.css").read_text(encoding="utf-8"))

    def test_o_nhap_tren_man_cam_ung_toi_thieu_16px(self):
        nguon = (CSS / "giao_dien.css").read_text(encoding="utf-8")
        cuoi = nguon[nguon.rindex("@media (max-width: 900px), (pointer: coarse)") :]
        self.assertIn("font-size: max(16px, 1em);", cuoi)
        self.assertNotIn("@layer", cuoi)

    def test_bo_hieu_ung_hien_dan_va_nho_len(self):
        """F08, F10: lưới thuốc không còn ẩn rồi hiện dần, thẻ không nhô lên khi rê chuột."""
        self.assertNotIn("hieu-ung-cuon", JS_GIAO_DIEN.read_text(encoding="utf-8"))
        khach = (CSS / "khach.css").read_text(encoding="utf-8")
        self.assertNotIn("hieu-ung-cuon", khach)
        nho_len = re.findall(r":hover[^{]*\{[^}]*translateY", khach)
        self.assertEqual(nho_len, [], "Còn hiệu ứng nhô lên khi rê chuột.")


class ThanhPhanDungChungTests(SimpleTestCase):
    def test_thong_bao_phan_biet_muc_do(self):
        cac_tin = [
            Message(messages.ERROR, "Đơn đã quá hạn giữ."),
            Message(messages.WARNING, "Hãy kiểm tra lại địa chỉ."),
            Message(messages.SUCCESS, "Đã lập phiếu bán."),
            Message(messages.INFO, "Có 2 đơn mới."),
        ]
        html = render_to_string("components/_thong_bao.html", {"messages": cac_tin})
        self.assertRegex(
            html, r'class="thong-bao thong-bao-loi" role="alert"[^>]*>\s*<i data-lucide="circle-x"'
        )
        self.assertIn("<strong>Chưa thực hiện được:</strong> Đơn đã quá hạn giữ.", html)
        self.assertIn('class="thong-bao thong-bao-canh-bao" role="alert"', html)
        self.assertIn('class="thong-bao thong-bao-thanh-cong" role="status"', html)
        self.assertIn('class="thong-bao thong-bao-thong-tin" role="status"', html)
        self.assertEqual(html.count("data-dong-thong-bao"), 4)

    def test_nhan_trang_thai_theo_muc(self):
        html = render_to_string(
            "components/_nhan_trang_thai.html", {"nhan": "Gửi lỗi", "muc": "loi"}
        )
        self.assertIn('class="nhan-trang-thai nhan-loi"', html)
        mac_dinh = render_to_string("components/_nhan_trang_thai.html", {"nhan": "Đã đóng"})
        self.assertIn("nhan-trung-tinh", mac_dinh)

    def test_nut_va_hop_thoai_xac_nhan(self):
        nut = render_to_string(
            "components/_nut.html",
            {
                "nhan": "Lưu phiếu",
                "loai": "submit",
                "xac_nhan": "Phiếu không sửa được sau khi lưu.",
            },
        )
        self.assertIn('type="submit"', nut)
        self.assertIn('data-xac-nhan="Phiếu không sửa được sau khi lưu."', nut)
        hop = render_to_string("components/_hop_thoai.html")
        self.assertIn('id="hop-thoai-xac-nhan"', hop)
        self.assertIn('value="huy"', hop)
        self.assertIn("Quay lại kiểm tra", hop)
        self.assertIn('value="dong-y"', hop)
        js = JS_GIAO_DIEN.read_text(encoding="utf-8")
        self.assertIn("data-xac-nhan", js)
        self.assertIn("requestSubmit", js)

    def test_bang_rong_va_trang_thai_rong(self):
        bang = render_to_string(
            "components/_bang.html",
            {
                "cac_cot": ["Thuốc", "Số lượng"],
                "cac_dong": [],
                "cot_so": [2],
                "chu_rong": "Chưa có phiếu.",
            },
        )
        self.assertIn('<tr class="hang-trong"><td colspan="2">Chưa có phiếu.</td></tr>', bang)
        self.assertIn('<th scope="col" class="o-so">Số lượng</th>', bang)
        rong = render_to_string(
            "components/_trang_thai_rong.html",
            {"tieu_de": "Chưa có đơn", "duong_dan": "/thuoc/", "nhan_hanh_dong": "Xem thuốc"},
        )
        self.assertIn("<h2>Chưa có đơn</h2>", rong)
        self.assertIn('<a class="nut" href="/thuoc/">Xem thuốc</a>', rong)

    def test_trang_500_tu_du_khong_can_context(self):
        """QT-15: Django vẽ 500.html với context rỗng; trang không phụ thuộc menu, người dùng, CSDL."""
        html = render_to_string("500.html")
        self.assertIn("Hệ thống đang gặp sự cố", html)
        self.assertIn('href="/"', html)
        self.assertIn('href="/quan-ly/"', html)
        self.assertNotIn("Đăng nhập", html)
        self.assertNotIn("{%", html)


def _view_loi(request):
    raise RuntimeError("Lỗi thử cho trang 500")


urlpatterns = [path("loi-thu/", _view_loi)]


@override_settings(ROOT_URLCONF=__name__, DEBUG=False)
class Trang500Tests(TestCase):
    def test_loi_may_chu_hien_trang_500_doc_lap(self):
        self.client.raise_request_exception = False
        phan_hoi = self.client.get("/loi-thu/")
        self.assertEqual(phan_hoi.status_code, 500)
        self.assertContains(phan_hoi, "Hệ thống đang gặp sự cố", status_code=500)
        self.assertNotContains(phan_hoi, "RuntimeError", status_code=500)


class KhungHaiKhuTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()

    def _yeu_cau(self, duong_dan, nguoi):
        yeu_cau = RequestFactory().get(duong_dan)
        yeu_cau.user = nguoi
        yeu_cau.session = SessionStore()
        yeu_cau._messages = CookieStorage(yeu_cau)
        yeu_cau.resolver_match = resolve(duong_dan)
        return yeu_cau

    def test_khung_quan_ly_hien_loi_khac_thanh_cong(self):
        """CB-01, QT-02, F03 (nghiệp vụ): lỗi ở /quan-ly/ có lớp, vai trò và chữ dẫn riêng."""
        yeu_cau = self._yeu_cau(reverse("chung:bang_dieu_khien"), self.d.ql)
        messages.error(yeu_cau, "Đơn đã quá hạn giữ.")
        messages.success(yeu_cau, "Đã lập phiếu bán.")
        html = render_to_string("base.html", request=yeu_cau)
        self.assertIn('class="thong-bao thong-bao-loi" role="alert"', html)
        self.assertIn("Chưa thực hiện được:", html)
        self.assertIn('class="thong-bao thong-bao-thanh-cong" role="status"', html)
        self.assertNotIn('<p class="thong-bao" role="status">', html)

    def test_khung_khach_hien_canh_bao_mau_rieng(self):
        yeu_cau = self._yeu_cau("/", self.d.khach)
        messages.warning(yeu_cau, "Hệ thống đã chọn phương án thay thế.")
        html = render_to_string("khach/base.html", request=yeu_cau)
        self.assertIn('class="thong-bao thong-bao-canh-bao" role="alert"', html)

    def test_moi_trang_khach_co_o_tim_va_dang_xuat(self):
        """F03, F04: ô tìm thuốc và nút Đăng xuất có ở đầu trang mọi trang khách."""
        self.client.force_login(self.d.khach)
        url_tim = reverse("danh_muc:khach_thuoc_danh_sach")
        url_thoat = reverse("tai_khoan:dang_xuat")
        for duong_dan in (
            "/",
            url_tim,
            reverse("ban_hang:gio_hang"),
            reverse("webgis:ban_do"),
            reverse("tai_khoan:cua_toi"),
        ):
            with self.subTest(trang=duong_dan):
                html = self.client.get(duong_dan).content.decode()
                dau_trang = html[
                    html.index('<header class="dau-trang-khach">') : html.index("</header>")
                ]
                self.assertRegex(
                    dau_trang,
                    rf'<form class="o-tim-dau-trang" role="search" method="get" action="{url_tim}"',
                )
                self.assertIn('name="q"', dau_trang)
                self.assertIn(f'action="{url_thoat}"', dau_trang)
                self.assertIn(">Đăng xuất</button>", dau_trang)
                self.assertIn('id="hop-thoai-xac-nhan"', html)

    def test_o_tim_giu_tu_khoa_va_tieu_de_theo_thuong_hieu(self):
        html = self.client.get(
            reverse("danh_muc:khach_thuoc_danh_sach"), {"q": "panadol"}
        ).content.decode()
        self.assertIn('value="panadol"', html)
        trang_chu = self.client.get("/")
        ten = trang_chu.context["cua_hang"].ten_thuong_hieu
        self.assertRegex(trang_chu.content.decode(), rf"<title>[^<]*{re.escape(ten)}")

    def test_menu_tin_tuc_chi_hien_khi_co_bai(self):
        """F16: không dẫn khách tới trang Tin tức rỗng."""
        from ung_dung.noi_dung.models import TinTuc

        url_tin = reverse("noi_dung:khach_tin_tuc_danh_sach")
        self.assertNotContains(self.client.get("/"), f'href="{url_tin}"')
        TinTuc.objects.create(
            duong_dan_tin_tuc="phong-cum",
            tieu_de="Phòng cúm mùa mưa",
            tom_tat="Năm việc nên làm.",
            noi_dung_tin_tuc="<p>Rửa tay.</p>",
            nguoi_viet=self.d.admin,
        )
        self.assertContains(self.client.get("/"), f'href="{url_tin}"')

    def test_menu_quan_tri_du_muc_va_nhom_he_thong(self):
        """QT-01, QT-13: mọi trang có quyền đều có mục menu; Tài khoản, Nhóm quyền, Email ở nhóm Hệ thống."""
        self.client.force_login(self.d.admin)
        phan_hoi = self.client.get(reverse("chung:bang_dieu_khien"))
        ten_trong_menu = {m["ten"] for m in phan_hoi.context["menu_ung_dung"]}
        self.assertLessEqual(set(QUYEN_MENU), ten_trong_menu)
        cac_nhom = phan_hoi.context["menu_nhom"]
        self.assertEqual([n["nhan"] for n in cac_nhom], list(CAC_NHOM))
        he_thong = next(n for n in cac_nhom if n["nhan"] == "Hệ thống")
        self.assertEqual(
            [m["nhan"] for m in he_thong["cac_muc"]], ["Tài khoản", "Nhóm quyền", "Email hệ thống"]
        )
        self.assertFalse(he_thong["mo_san"])
        self.assertIn("Hệ thống", NHOM_THU_GON)
        self.assertContains(phan_hoi, reverse("danh_muc:danh_gia_danh_sach"))

        trang_tai_khoan = self.client.get(reverse("tai_khoan:danh_sach"))
        self.assertEqual(trang_tai_khoan.context["nhom_dang_chon"], "Hệ thống")
        he_thong = next(n for n in trang_tai_khoan.context["menu_nhom"] if n["nhan"] == "Hệ thống")
        self.assertTrue(he_thong["mo_san"])
        self.assertContains(trang_tai_khoan, '<nav class="duong-dan" aria-label="Vị trí trang">')

    def test_menu_theo_quyen_cua_nhan_vien(self):
        self.client.force_login(self.d.nv)
        menu = {
            m["ten"]
            for m in self.client.get(reverse("chung:bang_dieu_khien")).context["menu_ung_dung"]
        }
        self.assertEqual("danh_muc:danh_gia_danh_sach" in menu, co_quyen(self.d.nv, "danh_gia.xem"))
        self.assertEqual("tai_khoan:danh_sach" in menu, co_quyen(self.d.nv, "tai_khoan.xem"))

    def test_403_cua_nhan_su_nam_trong_khung_quan_ly_va_neu_ly_do(self):
        """QT-08: nhân sự bị từ chối ở /quan-ly/ vẫn ở khung quản lý, thấy lý do và lối về tổng quan."""
        self.client.force_login(self.d.nv)
        phan_hoi = self.client.get(reverse("tai_khoan:nhom_quyen_danh_sach"))
        self.assertEqual(phan_hoi.status_code, 403)
        self.assertContains(phan_hoi, 'class="khung-ung-dung"', status_code=403)
        self.assertNotContains(phan_hoi, 'class="khung-khach"', status_code=403)
        self.assertContains(phan_hoi, "Lý do:", status_code=403)
        self.assertContains(phan_hoi, f'href="{reverse("chung:bang_dieu_khien")}"', status_code=403)

    def test_403_cua_khach_o_quan_ly_dung_khung_khach(self):
        self.client.force_login(self.d.khach)
        phan_hoi = self.client.get(reverse("chung:bang_dieu_khien"))
        self.assertEqual(phan_hoi.status_code, 403)
        self.assertContains(phan_hoi, 'class="khung-khach"', status_code=403)
        self.assertContains(
            phan_hoi, "Trang này chỉ dành cho nhân viên nhà thuốc.", status_code=403
        )
        self.assertContains(phan_hoi, "Về trang chủ", status_code=403)

    @override_settings(DEBUG=False)
    def test_404_khach_co_o_tim_va_ve_trang_chu(self):
        phan_hoi = self.client.get("/khong-co-trang-nay/")
        self.assertContains(phan_hoi, "Về trang chủ", status_code=404)
        self.assertContains(phan_hoi, 'id="tim-thuoc-404"', status_code=404)
        self.assertNotContains(phan_hoi, "Về trang tổng quan", status_code=404)

    @override_settings(DEBUG=False)
    def test_404_cua_nhan_su_o_quan_ly_dung_khung_quan_ly(self):
        self.client.force_login(self.d.ql)
        phan_hoi = self.client.get("/quan-ly/khong-co-trang-nay/")
        self.assertContains(phan_hoi, 'class="khung-ung-dung"', status_code=404)
        self.assertContains(phan_hoi, "Về trang tổng quan", status_code=404)
