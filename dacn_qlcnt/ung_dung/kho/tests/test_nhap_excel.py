from datetime import date, timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from ung_dung.danh_muc.models import QuyDoiBaoGoi
from ung_dung.kho.models import PhieuNhap
from ung_dung.kho.nhap_excel import COT, LoiTepExcel, doc_tep_nhap

from .du_lieu import tao_du_lieu


def tep_xlsx(*cac_hang, tieu_de=None):
    so = Workbook()
    trang = so.active
    trang.append(tieu_de or [nhan for _, nhan in COT])
    for hang in cac_hang:
        trang.append(list(hang))
    dem = BytesIO()
    so.save(dem)
    return SimpleUploadedFile("phieu.xlsx", dem.getvalue())


class NhapExcelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = tao_du_lieu()
        cls.hop = QuyDoiBaoGoi.objects.create(
            thuoc=cls.d.thuoc, ten_quy_doi_bao_goi="Hộp", he_so=10
        )

    def test_doc_o_so_o_chu_va_bao_goi(self):
        han = timezone.localdate() + timedelta(days=200)
        cac_dong, cac_loi = doc_tep_nhap(
            tep_xlsx(
                ["thuoc1", "LO-A", han, 3, "hộp", 1500.0],
                ["THUOC1", "LO-B", han.strftime("%d/%m/%Y"), "12", "", "12.000"],
                [None, None, None, None, None, None],
            )
        )
        self.assertEqual(cac_loi, [])
        self.assertEqual(cac_dong[0]["quy_doi_bao_goi"], self.hop.pk)
        self.assertEqual(cac_dong[0]["don_gia"], 1500)
        self.assertEqual(cac_dong[1]["don_gia"], 12000)
        self.assertEqual(cac_dong[1]["ngay_het_han"], han.isoformat())

    def test_bao_loi_theo_so_dong(self):
        _, cac_loi = doc_tep_nhap(
            tep_xlsx(
                ["KHONG-CO", "LO-A", date(2030, 1, 1), 1, "", 1],
                ["THUOC1", "LO/A", date(2030, 1, 1), 1, "", 1],
                ["THUOC1", "LO-C", date(2030, 1, 1), 1.5, "", 1],
            )
        )
        self.assertEqual([loi.split(":")[0] for loi in cac_loi], ["Dòng 2", "Dòng 3", "Dòng 4"])
        with self.assertRaises(LoiTepExcel):
            doc_tep_nhap(tep_xlsx(tieu_de=["Mã thuốc", "Số lượng"]))
        with self.assertRaises(LoiTepExcel):
            doc_tep_nhap(SimpleUploadedFile("hong.xlsx", b"khong phai excel"))

    def test_xem_truoc_khong_ghi_kho_roi_xac_nhan(self):
        self.client.force_login(self.d.nv)
        mau = self.client.get(reverse("kho:phieu_nhap_mau_excel"))
        self.assertEqual(load_workbook(BytesIO(mau.content)).sheetnames, ["Phiếu nhập", "Mã thuốc"])
        han = timezone.localdate() + timedelta(days=100)
        trang = self.client.post(
            reverse("kho:phieu_nhap_tao"),
            {"doc_excel": "1", "tep_excel": tep_xlsx(["THUOC1", "LO-X", han, 2, "Hộp", 900])},
        )
        self.assertContains(trang, "LO-X")
        self.assertContains(trang, 'name="form-INITIAL_FORMS" value="1"')
        self.assertFalse(PhieuNhap.objects.exists())
