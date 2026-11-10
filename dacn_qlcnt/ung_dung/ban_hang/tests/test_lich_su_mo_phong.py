from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from ung_dung.kho.models import LoThuoc, TonKho
from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton
from ung_dung.thanh_toan.models import GiaoDichThanhToan

from ..models import PhieuBan
from ..services.lich_su_mo_phong import tao_lich_su_ban_mo_phong


class LichSuMoPhongTests(TestCase):
    def test_ban_qua_nghiep_vu_khong_dung_ton_hien_co_va_lui_thoi_diem(self):
        d = tao_du_lieu()
        ton_cu = tao_ton(d, "LO-CU", ngay=200, luong=30)
        with self.assertRaises(PermissionDenied):
            tao_lich_su_ban_mo_phong(d.ql, so_ngay=7)
        tao_lich_su_ban_mo_phong(d.admin, so_ngay=7)
        cac_phieu = PhieuBan.objects.all()
        self.assertTrue(cac_phieu.exists())
        hom_nay = timezone.localdate()
        self.assertTrue(all(timezone.localdate(p.thoi_diem_tao) < hom_nay for p in cac_phieu))
        self.assertEqual(
            GiaoDichThanhToan.objects.filter(phieu_ban__in=cac_phieu).count(), cac_phieu.count()
        )
        # Chỉ chi nhánh có đủ quản lý và nhân viên mới có lịch sử; lô LS về 0, tồn cũ giữ nguyên.
        self.assertEqual(set(cac_phieu.values_list("chi_nhanh", flat=True)), {d.cn.pk})
        ton_cu.refresh_from_db()
        self.assertEqual(ton_cu.so_luong, 30)
        lo_mo_phong = LoThuoc.objects.get(ma_lo_thuoc__startswith="LS-")
        self.assertLess(lo_mo_phong.ngay_het_han, ton_cu.lo_thuoc.ngay_het_han)
        self.assertEqual(TonKho.objects.get(lo_thuoc=lo_mo_phong).so_luong, 0)
        with self.assertRaises(ValidationError):
            tao_lich_su_ban_mo_phong(d.admin, so_ngay=7)
