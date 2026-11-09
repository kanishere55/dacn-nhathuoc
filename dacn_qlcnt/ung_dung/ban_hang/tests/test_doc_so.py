from django.test import SimpleTestCase

from ..hoa_don import doc_so, doc_tien


class DocSoTests(SimpleTestCase):
    def test_cac_quy_tac_doc(self):
        for so, chu in (
            (0, "không"),
            (15, "mười lăm"),
            (21, "hai mươi mốt"),
            (24, "hai mươi tư"),
            (105, "một trăm linh năm"),
            (1005, "một nghìn không trăm linh năm"),
            (115000, "một trăm mười lăm nghìn"),
            (1050000, "một triệu không trăm năm mươi nghìn"),
            (2000000000, "hai tỷ"),
        ):
            with self.subTest(so=so):
                self.assertEqual(doc_so(so), chu)
        self.assertEqual(doc_tien(19500), "Mười chín nghìn năm trăm đồng")
