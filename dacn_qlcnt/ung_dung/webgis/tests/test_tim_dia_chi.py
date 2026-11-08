import io
import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class TimDiaChiTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("khach_tim", "Mk-test-2026!"))

    @mock.patch("ung_dung.webgis.services.dia_chi.time.sleep")
    @mock.patch("ung_dung.webgis.services.dia_chi.urlopen")
    def test_tim_qua_may_chu_gioi_han_viet_nam(self, urlopen, _ngu):
        urlopen.return_value = mock.MagicMock()
        urlopen.return_value.__enter__.return_value = io.BytesIO(
            json.dumps(
                [{"display_name": "Chợ Bến Thành", "lat": "10.772", "lon": "106.698"}]
            ).encode()
        )
        ket_qua = self.client.get(reverse("webgis:tim_dia_chi"), {"q": "chợ bến thành"}).json()
        self.assertEqual(ket_qua["ket_qua"][0]["vi_do"], 10.772)
        yeu_cau = urlopen.call_args.args[0]
        self.assertIn("countrycodes=vn", yeu_cau.full_url)
        self.assertIn("DACN", yeu_cau.get_header("User-agent"))

    def test_can_dang_nhap_va_tu_khoa_du_dai(self):
        self.assertEqual(
            self.client.get(reverse("webgis:tim_dia_chi"), {"q": "ab"}).status_code, 400
        )
        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("webgis:tim_dia_chi"), {"q": "abc"}).status_code, 403
        )

    @mock.patch("ung_dung.webgis.services.dia_chi.urlopen", side_effect=TimeoutError())
    def test_dich_vu_loi_tra_503(self, _urlopen):
        phan_hoi_api = self.client.get(
            reverse("webgis:dia_chi_tu_toa_do"), {"vi_do": 10.77, "kinh_do": 106.7}
        )
        self.assertEqual(phan_hoi_api.status_code, 503)
