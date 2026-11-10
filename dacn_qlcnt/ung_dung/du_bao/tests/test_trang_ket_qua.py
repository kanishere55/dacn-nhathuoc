from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from ung_dung.kho.tests.du_lieu import tao_du_lieu

from ..models import DuBaoBayNgay, KetQuaMoHinh, LanThucNghiem, NguonDuLieu, QuanSatBanHang
from ..selectors import TEN_MO_HINH

MA = "N02BE"


def tao_ket_qua():
    nguon = NguonDuLieu.objects.create(
        ten_nguon_du_lieu="Nguồn thử", bam_sha256="a" * 64, don_vi_nguon="Đơn vị nguồn"
    )
    dau = date(2019, 1, 1)
    QuanSatBanHang.objects.bulk_create(
        QuanSatBanHang(
            nguon_du_lieu=nguon,
            ma_atc_nguon=MA,
            ngay_ban=dau + timedelta(days=i),
            so_luong=10 + (i % 7),
        )
        for i in range(60)
    )
    lan = LanThucNghiem.objects.create(
        nguon_du_lieu=nguon,
        ngay_chot_huan_luyen=dau + timedelta(days=30),
        ngay_chot_xac_thuc=dau + timedelta(days=45),
        ngay_chot_kiem_thu=dau + timedelta(days=59),
        cau_hinh={"dac_trung": ["thu"], "sarimax_theo_nhom": {}},
    )
    for i, ma in enumerate(TEN_MO_HINH):
        ket_qua = KetQuaMoHinh.objects.create(
            lan_thuc_nghiem=lan,
            ma_atc_nguon=MA,
            mo_hinh=ma,
            mae_xac_thuc=5 + i,
            rmse_xac_thuc=6 + i,
            mae_kiem_thu=7 - i,
            rmse_kiem_thu=8,
            duoc_chon=i == 0,
        )
        for ngay in range(46, 52):
            DuBaoBayNgay.objects.create(
                ket_qua_mo_hinh=ket_qua,
                ngay_goc=dau + timedelta(days=ngay),
                ky_danh_gia="kiem_thu",
                so_luong_du_bao=80 + i,
                so_luong_thuc_te=84,
            )
        if i == 0:
            DuBaoBayNgay.objects.create(
                ket_qua_mo_hinh=ket_qua,
                ngay_goc=dau + timedelta(days=59),
                ky_danh_gia="tuong_lai",
                so_luong_du_bao=90,
            )
    return lan


class TrangDuBaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        cls.lan = tao_ket_qua()

    def test_trang_hien_tong_quan_va_ty_le_sai_so(self):
        self.client.force_login(self.d.admin)
        trang = self.client.get(reverse("du_bao:ket_qua"))
        self.assertContains(trang, "Dự báo lượng bán theo nhóm thuốc ATC")
        self.assertContains(trang, 'data-nhom="N02BE"')
        self.assertContains(trang, "Hồi quy tuyến tính")
        nhom = trang.context["cac_nhom"][0]
        # MAE kiểm thử của mô hình được chọn 7, trung bình thực tế 84 → khoảng 8,3%.
        self.assertAlmostEqual(nhom["ty_le_sai_so"], 7 / 84 * 100)
        self.assertEqual(nhom["muc_sai_so"], "thap")
        self.assertEqual([m["ma"] for m in nhom["cac_mo_hinh"]], list(TEN_MO_HINH))
        self.assertTrue(nhom["cac_mo_hinh"][-1]["tot_nhat_test"])

    def test_api_nhom_tra_du_lieu_bieu_do_va_kiem_quyen(self):
        url = reverse("du_bao:chi_tiet_nhom", args=[MA])
        self.client.force_login(self.d.admin)
        du_lieu = self.client.get(url).json()
        self.assertEqual(du_lieu["mo_hinh_chon"], "hoi_quy_tuyen_tinh")
        self.assertEqual(len(du_lieu["kiem_thu"]["ngay"]), 6)
        self.assertEqual(set(du_lieu["kiem_thu"]["du_bao"]), set(TEN_MO_HINH))
        self.assertEqual(du_lieu["kiem_thu"]["thuc_te"][0], 84)
        self.assertEqual(len(du_lieu["theo_thu"]), 7)
        self.assertEqual(du_lieu["tuong_lai"]["so_luong"], 90)
        self.assertEqual(
            self.client.get(reverse("du_bao:chi_tiet_nhom", args=["R99"])).status_code, 404
        )
        self.client.force_login(self.d.khach)
        self.assertEqual(self.client.get(url).status_code, 403)
