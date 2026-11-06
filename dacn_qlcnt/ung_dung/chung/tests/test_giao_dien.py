from functools import wraps

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import ResolverMatch
from django.views import View
from rest_framework.views import APIView

from ung_dung.chung.nhan_dien_trang import nhan_dien_trang


class TrangDangLop(View):
    pass


class APIDangLop(APIView):
    pass


class NhanDienTrangTests(SimpleTestCase):
    @override_settings(DEBUG=True, HIEN_NHAN_DIEN_TRANG=True)
    def test_hien_du_ba_thanh_phan(self):
        phan_hoi = self.client.get("/")
        self.assertEqual(phan_hoi.status_code, 200)
        for muc in (
            "chung:trang_chu",
            "ung_dung/chung/views.py",
            "trang_chu",
            "chung/trang_chu.html",
        ):
            self.assertContains(phan_hoi, muc)

    @override_settings(DEBUG=False, HIEN_NHAN_DIEN_TRANG=True)
    def test_khong_lo_duong_dan_khi_tat_debug(self):
        phan_hoi = self.client.get("/")
        self.assertNotContains(phan_hoi, "ung_dung/chung/views.py")

    @override_settings(DEBUG=True, HIEN_NHAN_DIEN_TRANG=False)
    def test_co_the_tat_nhan_dien(self):
        self.assertNotContains(self.client.get("/"), "ung_dung/chung/views.py")

    @override_settings(DEBUG=False)
    def test_trang_404_khong_lo_ky_thuat(self):
        phan_hoi = self.client.get("/duong-dan-khong-ton-tai/")
        self.assertEqual(phan_hoi.status_code, 404)
        self.assertContains(phan_hoi, "Không tìm thấy trang", status_code=404)
        self.assertNotContains(phan_hoi, "Traceback", status_code=404)
        self.assertNotContains(phan_hoi, 'aria-current="page"', status_code=404)

    def test_chi_danh_dau_tong_quan_khi_dang_o_trang_chu(self):
        self.assertContains(self.client.get("/"), 'aria-current="page"', count=1)

    def test_trang_403_khong_danh_dau_tong_quan(self):
        yeu_cau = RequestFactory().get("/khong-co-quyen/")
        yeu_cau.resolver_match = None
        trang = render_to_string("loi/403.html", request=yeu_cau)
        self.assertNotIn('aria-current="page"', trang)

    @override_settings(DEBUG=True, HIEN_NHAN_DIEN_TRANG=True)
    def test_nhan_dien_class_view_va_drf_dung_tep_cua_class(self):
        for lop in (TrangDangLop, APIDangLop):
            with self.subTest(lop=lop.__name__):
                yeu_cau = RequestFactory().get("/thu/")
                yeu_cau.resolver_match = ResolverMatch(lop.as_view(), (), {}, url_name="thu")
                nhan = nhan_dien_trang(yeu_cau)["nhan_dien"]["view"]
                self.assertEqual(nhan, f"ung_dung/chung/tests/test_giao_dien.py → {lop.__name__}")
                self.assertNotIn(".venv/", nhan)

    @override_settings(DEBUG=True, HIEN_NHAN_DIEN_TRANG=True)
    def test_nhan_dien_function_view_co_decorator(self):
        def trang_thu(request):
            return HttpResponse()

        @wraps(trang_thu)
        def boc(request):
            return trang_thu(request)

        yeu_cau = RequestFactory().get("/thu/")
        yeu_cau.resolver_match = ResolverMatch(boc, (), {}, url_name="thu")
        self.assertEqual(
            nhan_dien_trang(yeu_cau)["nhan_dien"]["view"],
            "ung_dung/chung/tests/test_giao_dien.py → trang_thu",
        )
