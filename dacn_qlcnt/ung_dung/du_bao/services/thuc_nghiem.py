from importlib.metadata import version

import pandas as pd
from django.db import transaction

from thuc_nghiem_du_bao.danh_gia import danh_gia_nhom, lay_moc
from thuc_nghiem_du_bao.du_lieu import CAC_NHOM_ATC, DAC_TRUNG, SO_NGAY_DU_BAO
from thuc_nghiem_du_bao.mo_hinh import THAM_SO

from ..models import DuBaoBayNgay, KetQuaMoHinh, LanThucNghiem, QuanSatBanHang


def chay_thuc_nghiem(nguon):
    cac_hang = QuanSatBanHang.objects.filter(nguon_du_lieu=nguon).values_list(
        "ngay_ban", "ma_atc_nguon", "so_luong"
    )
    bang = pd.DataFrame(list(cac_hang), columns=["ngay", "nhom", "luong"])
    if bang.empty or set(bang["nhom"]) != set(CAC_NHOM_ATC):
        raise ValueError("Nguồn chưa có đủ dữ liệu cho tám nhóm ATC.")
    bang["ngay"] = pd.to_datetime(bang["ngay"])
    chuoi = bang.pivot(index="ngay", columns="nhom", values="luong").sort_index()
    if chuoi.isna().any().any() or not chuoi.index.equals(
        pd.date_range(chuoi.index.min(), chuoi.index.max(), freq="D")
    ):
        raise ValueError("Dữ liệu trong DB có ngày thiếu hoặc không đầy đủ tám nhóm.")
    moc = lay_moc(chuoi.index)
    cac_nhom = {nhom: danh_gia_nhom(chuoi[nhom], *moc) for nhom in CAC_NHOM_ATC}
    return luu_ket_qua(nguon, moc, cac_nhom)


@transaction.atomic
def luu_ket_qua(nguon, moc, cac_nhom):
    lan = LanThucNghiem.objects.create(
        nguon_du_lieu=nguon,
        ngay_chot_huan_luyen=moc[0].date(),
        ngay_chot_xac_thuc=moc[1].date(),
        ngay_chot_kiem_thu=moc[2].date(),
        cau_hinh={
            "mo_hinh": THAM_SO,
            "sarimax_theo_nhom": {
                nhom: {"tham_so_chon": sarimax["tham_so"], "khao_sat": sarimax["khao_sat"]}
                for nhom, (_, cac_ket_qua) in cac_nhom.items()
                for sarimax in (cac_ket_qua["sarimax"],)
            },
            "dac_trung": DAC_TRUNG,
            "so_ngay_du_bao": SO_NGAY_DU_BAO,
            "cach_chon": "MAE tập xác thực, sau đó RMSE tập xác thực và tên mô hình",
            "thu_vien": {
                ten: version(ten) for ten in ("pandas", "scikit-learn", "xgboost", "statsmodels")
            },
        },
    )
    for nhom, (duoc_chon, cac_ket_qua) in cac_nhom.items():
        for ten, ket_qua in cac_ket_qua.items():
            mae_val, rmse_val = ket_qua["sai_so_validation"]
            mae_kiem_thu, rmse_kiem_thu = ket_qua["sai_so_test"]
            mo_hinh = KetQuaMoHinh.objects.create(
                lan_thuc_nghiem=lan,
                ma_atc_nguon=nhom,
                mo_hinh=ten,
                mae_xac_thuc=mae_val,
                rmse_xac_thuc=rmse_val,
                mae_kiem_thu=mae_kiem_thu,
                rmse_kiem_thu=rmse_kiem_thu,
                duoc_chon=ten == duoc_chon,
            )
            for ky in ("xac_thuc", "kiem_thu", "tuong_lai"):
                if ky not in ket_qua:
                    continue
                tap, cac_du_bao = ket_qua[ky]
                DuBaoBayNgay.objects.bulk_create(
                    [
                        DuBaoBayNgay(
                            ket_qua_mo_hinh=mo_hinh,
                            ngay_goc=ngay.date(),
                            ky_danh_gia=ky,
                            so_luong_du_bao=float(du_bao),
                            so_luong_thuc_te=None if ky == "tuong_lai" else float(thuc_te),
                        )
                        for (ngay, thuc_te), du_bao in zip(
                            tap["muc_tieu"].items(), cac_du_bao, strict=True
                        )
                    ],
                    batch_size=1000,
                )
    return lan
