from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TransactionTestCase

from ung_dung.danh_muc.models import ChiNhanh, Thuoc
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton

from ..models import PhieuBan
from ..services.phieu_ban import ban_tai_quay


class DongThoiTests(TransactionTestCase):
    def test_hai_ket_noi_cung_ban_luong_cuoi_khong_am_kho(self):
        d = tao_du_lieu()
        ton = tao_ton(d, luong=10)
        rao = Barrier(2)

        def ban():
            try:
                nguoi = get_user_model().objects.get(pk=d.nv.pk)
                cn = ChiNhanh.objects.get(pk=d.cn.pk)
                thuoc = Thuoc.objects.get(pk=d.thuoc.pk)
                rao.wait(timeout=10)
                try:
                    ban_tai_quay(nguoi, cn, [{"thuoc": thuoc, "so_luong": 7}])
                    return "dat"
                except ValidationError:
                    return "thieu"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as nhom:
            cac_luot = [nhom.submit(ban) for _ in range(2)]
            ket_qua = [luot.result(timeout=20) for luot in cac_luot]
        self.assertCountEqual(ket_qua, ["dat", "thieu"])
        ton.refresh_from_db()
        self.assertEqual(ton.so_luong, 3)
        self.assertEqual(PhieuBan.objects.count(), 1)
