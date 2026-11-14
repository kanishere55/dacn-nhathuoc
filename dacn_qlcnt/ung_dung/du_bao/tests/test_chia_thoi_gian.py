import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from thuc_nghiem_du_bao.danh_gia import danh_gia_nhom, lay_moc
from thuc_nghiem_du_bao.du_lieu import DAC_TRUNG, chia_theo_thoi_gian, tao_mau
from thuc_nghiem_du_bao.mo_hinh import (
    CAU_HINH_SARIMAX,
    SO_CAP_FOURIER_NAM,
    THAM_SO,
    bien_ngoai_sinh,
    du_doan,
)


class DuBaoTests(SimpleTestCase):
    def setUp(self):
        ngau_nhien = np.random.default_rng(42)
        ngay = pd.date_range("2014-01-02", periods=120, freq="D")
        self.chuoi = pd.Series(8 + ngau_nhien.normal(0, 1, len(ngay)), index=ngay)

    def test_nhan_bay_ngay_va_khong_chong_train_validation_test(self):
        mau = tao_mau(self.chuoi)
        m1, m2, m3 = lay_moc(self.chuoi.index)
        train, val, test = chia_theo_thoi_gian(mau, m1, m2, m3)
        self.assertLessEqual(train["ngay_ket_thuc_nhan"].max(), val.index.min())
        self.assertLessEqual(val["ngay_ket_thuc_nhan"].max(), test.index.min())
        ngay = val.index[0]
        self.assertAlmostEqual(
            mau.loc[ngay, "muc_tieu"],
            self.chuoi.loc[ngay + pd.Timedelta(days=1) : ngay + pd.Timedelta(days=7)].sum(),
        )

    def test_thay_du_lieu_tuong_lai_khong_doi_dac_trung_va_du_bao(self):
        m1, m2, m3 = lay_moc(self.chuoi.index)
        mau = tao_mau(self.chuoi)
        train, val, _ = chia_theo_thoi_gian(mau, m1, m2, m3)
        ngay = val.index[2]
        chuoi_khac = self.chuoi.copy()
        chuoi_khac.loc[chuoi_khac.index > ngay] *= 100
        mau_khac = tao_mau(chuoi_khac)
        train_khac, val_khac, _ = chia_theo_thoi_gian(mau_khac, m1, m2, m3)
        pd.testing.assert_frame_equal(mau.loc[:ngay, DAC_TRUNG], mau_khac.loc[:ngay, DAC_TRUNG])
        self.assertNotEqual(mau.loc[ngay, "muc_tieu"], mau_khac.loc[ngay, "muc_tieu"])
        for ten in ("hoi_quy_tuyen_tinh", "sarimax"):
            with self.subTest(ten=ten):
                goc = du_doan(ten, self.chuoi, m1, train, val.loc[:ngay])
                thay = du_doan(ten, chuoi_khac, m1, train_khac, val_khac.loc[:ngay])
                np.testing.assert_allclose(goc, thay)

    def test_chay_du_nam_mo_hinh_va_chon_bang_validation(self):
        ten, ket_qua = danh_gia_nhom(self.chuoi, *lay_moc(self.chuoi.index))
        self.assertEqual(set(ket_qua), set(THAM_SO))
        self.assertEqual(ten, min(ket_qua, key=lambda m: (*ket_qua[m]["sai_so_validation"], m)))
        cac_luot = ket_qua["sarimax"]["khao_sat"]
        self.assertEqual(len(cac_luot), len(CAU_HINH_SARIMAX))
        self.assertTrue(any(luot["tham_so"].get("ngoai_sinh") for luot in cac_luot))
        tot_nhat = min(
            (luot for luot in cac_luot if luot["hoi_tu"]),
            key=lambda luot: (luot["mae"], luot["rmse"]),
        )
        self.assertEqual(ket_qua["sarimax"]["tham_so"], tot_nhat["tham_so"])
        for muc in ket_qua.values():
            self.assertTrue(np.isfinite(muc["sai_so_test"]).all())
        self.assertEqual(len(ket_qua[ten]["tuong_lai"][1]), 1)

    def test_sarimax_co_bien_ngoai_sinh_khong_dung_du_lieu_tuong_lai(self):
        """Cấu hình có số hạng Fourier theo năm: đổi lượng bán sau ngày gốc không đổi dự báo."""
        tham_so = next(c for c in CAU_HINH_SARIMAX if c.get("ngoai_sinh"))
        m1, m2, m3 = lay_moc(self.chuoi.index)
        mau = tao_mau(self.chuoi)
        train, val, _ = chia_theo_thoi_gian(mau, m1, m2, m3)
        ngay = val.index[2]
        chuoi_khac = self.chuoi.copy()
        chuoi_khac.loc[chuoi_khac.index > ngay] *= 100
        train_khac, val_khac, _ = chia_theo_thoi_gian(tao_mau(chuoi_khac), m1, m2, m3)
        goc = du_doan("sarimax", self.chuoi, m1, train, val.loc[:ngay], tham_so=tham_so)
        thay = du_doan("sarimax", chuoi_khac, m1, train_khac, val_khac.loc[:ngay], tham_so=tham_so)
        np.testing.assert_allclose(goc, thay)

    def test_bien_ngoai_sinh_chi_phu_thuoc_ngay_lich(self):
        cac_ngay = pd.date_range("2018-01-01", periods=400, freq="D")
        ma_tran = bien_ngoai_sinh(cac_ngay)
        self.assertEqual(ma_tran.shape, (400, 2 * SO_CAP_FOURIER_NAM))
        self.assertTrue((np.abs(ma_tran) <= 1).all())
        # Cùng ngày trong năm thì cùng giá trị, bất kể năm nào.
        np.testing.assert_allclose(ma_tran[0], bien_ngoai_sinh(pd.DatetimeIndex(["2019-01-01"]))[0])
