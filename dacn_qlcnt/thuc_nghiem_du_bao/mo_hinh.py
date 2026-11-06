import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.tree import DecisionTreeRegressor
from statsmodels.tsa.statespace.sarimax import SARIMAX
from xgboost import XGBRegressor

from .du_lieu import DAC_TRUNG, SO_NGAY_DU_BAO

THAM_SO = {
    "hoi_quy_tuyen_tinh": {},
    "cay_quyet_dinh": {"max_depth": 5, "min_samples_leaf": 7, "random_state": 42},
    "rung_ngau_nhien": {
        "n_estimators": 100,
        "max_depth": 8,
        "min_samples_leaf": 5,
        "random_state": 42,
        "n_jobs": 1,
    },
    "xgboost": {
        "n_estimators": 100,
        "max_depth": 3,
        "learning_rate": 0.05,
        "random_state": 42,
        "n_jobs": 1,
    },
    "sarimax": {"order": (1, 0, 0), "seasonal_order": (1, 0, 0, 7), "trend": "c"},
}
CAU_HINH_SARIMAX = (
    THAM_SO["sarimax"],
    {"order": (1, 0, 0), "seasonal_order": (0, 0, 0, 0), "trend": "c"},
    {"order": (1, 0, 0), "seasonal_order": (1, 0, 0, 7), "trend": "n"},
)
CAC_LOP = {
    "hoi_quy_tuyen_tinh": LinearRegression,
    "cay_quyet_dinh": DecisionTreeRegressor,
    "rung_ngau_nhien": RandomForestRegressor,
    "xgboost": XGBRegressor,
}


class KhongHoiTu(ValueError):
    pass


def du_doan_sarimax(chuoi, ngay_fit_cuoi, cac_ngay_goc, tham_so):
    vi_tri_cuoi = chuoi.index.get_loc(ngay_fit_cuoi)
    fit = SARIMAX(chuoi.iloc[: vi_tri_cuoi + 1].to_numpy(), **tham_so).fit(disp=False, maxiter=200)
    if not fit.mle_retvals.get("converged"):
        raise KhongHoiTu(f"SARIMAX không hội tụ trên tập kết thúc {ngay_fit_cuoi.date()}.")
    ket_qua = []
    for ngay in cac_ngay_goc:
        vi_tri = chuoi.index.get_loc(ngay)
        if vi_tri < vi_tri_cuoi:
            raise ValueError("Ngày gốc dự báo đứng trước dữ liệu đã fit.")
        if vi_tri > vi_tri_cuoi:
            fit = fit.extend(chuoi.iloc[vi_tri_cuoi + 1 : vi_tri + 1].to_numpy())
            vi_tri_cuoi = vi_tri
        ket_qua.append(fit.forecast(SO_NGAY_DU_BAO).sum())
    return np.asarray(ket_qua)


def du_doan(ten, chuoi, moc, tap_fit, tap_du_doan, *, tham_so=None):
    if tap_fit.empty or tap_du_doan.empty or tap_fit["ngay_ket_thuc_nhan"].max() > moc:
        raise ValueError("Tập fit rỗng, tập dự báo rỗng hoặc nhãn vượt mốc được phép.")
    if tap_du_doan.index.min() < moc:
        raise ValueError("Ngày gốc của tập dự báo đứng trước mốc fit.")
    if tham_so is None:
        tham_so = THAM_SO[ten]
    if ten == "sarimax":
        ket_qua = du_doan_sarimax(chuoi, moc, tap_du_doan.index, tham_so)
    else:
        mo_hinh = CAC_LOP[ten](**tham_so)
        mo_hinh.fit(tap_fit[DAC_TRUNG], tap_fit["muc_tieu"])
        ket_qua = mo_hinh.predict(tap_du_doan[DAC_TRUNG])
    if not np.isfinite(ket_qua).all():
        raise ValueError(f"Mô hình {ten} trả kết quả không hữu hạn.")
    return np.maximum(0, ket_qua)


def tinh_sai_so(tap, du_bao):
    return (
        float(mean_absolute_error(tap["muc_tieu"], du_bao)),
        float(root_mean_squared_error(tap["muc_tieu"], du_bao)),
    )
