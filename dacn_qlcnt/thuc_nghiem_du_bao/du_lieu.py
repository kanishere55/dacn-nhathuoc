import pandas as pd

CAC_NHOM_ATC = ("M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06")
SO_NGAY_DU_BAO = 7
DAC_TRUNG = [
    "ngay_hien_tai",
    "ngay_truoc",
    "tuan_truoc",
    "trung_binh_7",
    "trung_binh_28",
    "thu",
    "thang",
]


def tao_mau(chuoi):
    mau = pd.DataFrame(
        {
            "ngay_hien_tai": chuoi,
            "ngay_truoc": chuoi.shift(1),
            "tuan_truoc": chuoi.shift(7),
            "trung_binh_7": chuoi.rolling(7).mean(),
            "trung_binh_28": chuoi.rolling(28).mean(),
            "thu": chuoi.index.dayofweek,
            "thang": chuoi.index.month,
        }
    )
    cac_ngay_sau = pd.concat([chuoi.shift(-i) for i in range(1, SO_NGAY_DU_BAO + 1)], axis=1)
    mau["muc_tieu"] = cac_ngay_sau.sum(axis=1, min_count=SO_NGAY_DU_BAO)
    mau["ngay_ket_thuc_nhan"] = mau.index + pd.Timedelta(days=SO_NGAY_DU_BAO)
    return mau.dropna(subset=DAC_TRUNG)


def chia_theo_thoi_gian(mau, moc_train, moc_validation, moc_test):
    ket_thuc = mau["ngay_ket_thuc_nhan"]
    co_nhan = mau["muc_tieu"].notna()
    return (
        mau.loc[co_nhan & (ket_thuc <= moc_train)],
        mau.loc[co_nhan & (mau.index >= moc_train) & (ket_thuc <= moc_validation)],
        mau.loc[co_nhan & (mau.index >= moc_validation) & (ket_thuc <= moc_test)],
    )
