import pandas as pd

from .du_lieu import chia_theo_thoi_gian, tao_mau
from .mo_hinh import CAU_HINH_SARIMAX, THAM_SO, KhongHoiTu, du_doan, tinh_sai_so


def chon_sarimax(chuoi, moc_train, train, validation):
    cac_luot = []
    tot_nhat = None
    for tham_so in CAU_HINH_SARIMAX:
        try:
            du_bao = du_doan("sarimax", chuoi, moc_train, train, validation, tham_so=tham_so)
        except KhongHoiTu:
            cac_luot.append({"tham_so": tham_so, "hoi_tu": False})
            continue
        sai_so = tinh_sai_so(validation, du_bao)
        cac_luot.append({"tham_so": tham_so, "hoi_tu": True, "mae": sai_so[0], "rmse": sai_so[1]})
        if tot_nhat is None or sai_so < tot_nhat[0]:
            tot_nhat = sai_so, tham_so, du_bao
    if tot_nhat is None:
        raise KhongHoiTu("Tất cả cấu hình SARIMAX đều không hội tụ trên tập huấn luyện.")
    _, tham_so, du_bao = tot_nhat
    return tham_so, du_bao, cac_luot


def danh_gia_nhom(chuoi, moc_train, moc_validation, moc_test):
    mau = tao_mau(chuoi)
    train, validation, test = chia_theo_thoi_gian(mau, moc_train, moc_validation, moc_test)
    train_validation = mau.loc[
        mau["muc_tieu"].notna() & (mau["ngay_ket_thuc_nhan"] <= moc_validation)
    ]
    cac_ket_qua = {}
    for ten, tham_so in THAM_SO.items():
        cac_luot = []
        if ten == "sarimax":
            tham_so, du_bao, cac_luot = chon_sarimax(chuoi, moc_train, train, validation)
        else:
            du_bao = du_doan(ten, chuoi, moc_train, train, validation, tham_so=tham_so)
        cac_ket_qua[ten] = {
            "sai_so_validation": tinh_sai_so(validation, du_bao),
            "xac_thuc": (validation, du_bao),
            "tham_so": tham_so,
            "khao_sat": cac_luot,
        }
    # Chốt lựa chọn trước khi tính bất kỳ sai số nào của tập test.
    duoc_chon = min(cac_ket_qua, key=lambda ten: (*cac_ket_qua[ten]["sai_so_validation"], ten))
    for ten, ket_qua in cac_ket_qua.items():
        du_bao = du_doan(
            ten, chuoi, moc_validation, train_validation, test, tham_so=ket_qua["tham_so"]
        )
        ket_qua["sai_so_test"] = tinh_sai_so(test, du_bao)
        ket_qua["kiem_thu"] = (test, du_bao)
    tap_cuoi = mau.loc[mau["muc_tieu"].notna() & (mau["ngay_ket_thuc_nhan"] <= moc_test)]
    ngay_goc_cuoi = mau.loc[[moc_test]]
    tuong_lai = du_doan(
        duoc_chon,
        chuoi,
        moc_test,
        tap_cuoi,
        ngay_goc_cuoi,
        tham_so=cac_ket_qua[duoc_chon]["tham_so"],
    )
    cac_ket_qua[duoc_chon]["tuong_lai"] = (ngay_goc_cuoi, tuong_lai)
    return duoc_chon, cac_ket_qua


def lay_moc(ngay):
    ngay = pd.DatetimeIndex(ngay)
    if len(ngay) < 100:
        raise ValueError("Cần ít nhất 100 ngày liên tục để chia tập và tạo đặc trưng.")
    return ngay[len(ngay) * 6 // 10 - 1], ngay[len(ngay) * 8 // 10 - 1], ngay[-1]
