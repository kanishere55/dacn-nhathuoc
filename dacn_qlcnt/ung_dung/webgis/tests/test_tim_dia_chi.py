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

    @mock.patch("ung_dung.webgis.services.dia_chi.time.sleep")
    @mock.patch("ung_dung.webgis.services.dia_chi.urlopen")
    def test_khong_ra_thi_thu_viet_gon_va_bao_gan_dung(self, urlopen, _ngu):
        """Gõ số nhà kèm tên phường cũ: tìm nguyên văn rỗng, bỏ phần sau dấu phẩy thì ra đường."""

        def tra_loi(yeu_cau, timeout):
            rong = "B%E1%BA%BFn+Ngh%C3%A9" in yeu_cau.full_url  # còn "Bến Nghé" thì không ra
            du_lieu = (
                []
                if rong
                else [{"display_name": "Lê Lợi, Phường Sài Gòn", "lat": "10.774", "lon": "106.701"}]
            )
            phan_hoi = mock.MagicMock()
            phan_hoi.__enter__.return_value = io.BytesIO(json.dumps(du_lieu).encode())
            return phan_hoi

        urlopen.side_effect = tra_loi
        ket_qua = self.client.get(
            reverse("webgis:tim_dia_chi"), {"q": "45 Lê Lợi, Bến Nghé"}
        ).json()
        self.assertTrue(ket_qua["gan_dung"])
        self.assertEqual(ket_qua["ket_qua"][0]["dia_chi"], "Lê Lợi, Phường Sài Gòn")
        self.assertEqual(urlopen.call_count, 2)

    @mock.patch("ung_dung.webgis.services.dia_chi.time.sleep")
    @mock.patch("ung_dung.webgis.services.dia_chi.urlopen")
    def test_tim_ra_ngay_thi_khong_gan_dung(self, urlopen, _ngu):
        urlopen.return_value = mock.MagicMock()
        urlopen.return_value.__enter__.return_value = io.BytesIO(
            json.dumps(
                [{"display_name": "Chợ Bến Thành", "lat": "10.772", "lon": "106.698"}]
            ).encode()
        )
        ket_qua = self.client.get(reverse("webgis:tim_dia_chi"), {"q": "chợ bến thành"}).json()
        self.assertFalse(ket_qua["gan_dung"])
        self.assertEqual(urlopen.call_count, 1)

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
