"""Tầng 1 – Tiền xử lý dữ liệu (Slide 1.1, Slide 2.2, Slide 4).

Các hàm trong module này đều **không sửa dữ liệu gốc**: chúng trả về bản sao
đã xử lý, kèm nhật ký biến đổi để ghi vào báo cáo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import PreprocessConfig


# ── Xử lý giá trị thiếu & trùng lặp ──────────────────────────────────────────
def handle_missing(
    df: pd.DataFrame,
    config: PreprocessConfig | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Điền giá trị rỗng cho các cột chỉ dùng để hiển thị.

    Slide 2.2 – ``fillna(x)``. Các cột khóa (mã đơn, mã khách, mã hàng) tuyệt đối
    không được điền vì sai lệch ở đó sẽ làm sai kết quả phân tích.
    """
    config = config or PreprocessConfig()
    log: list[str] = []
    df = df.copy()
    for col in ("customer_name", "segment_desc"):
        if col not in df.columns:
            continue
        n = int(df[col].isna().sum())
        if n:
            df[col] = df[col].fillna(config.fill_missing_name)
            log.append(f"{col}: fillna({config.fill_missing_name!r}) cho {n} dòng")
    return df, log


def drop_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Slide 2.2 – ``drop_duplicates()``."""
    before = len(df)
    out = df.drop_duplicates().reset_index(drop=True)
    return out, before - len(out)


# ── Outlier theo IQR (Slide 4) ────────────────────────────────────────────────
@dataclass
class OutlierReport:
    """Kết quả phát hiện outlier theo quy tắc IQR."""

    column: str
    q1: float
    q3: float
    iqr: float
    lower_bound: float
    upper_bound: float
    n_outliers: int
    total: int
    notes: list[str] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        return self.n_outliers / self.total if self.total else 0.0


def detect_outliers_iqr(
    df: pd.DataFrame,
    column: str,
    multiplier: float = 1.5,
) -> OutlierReport:
    """Slide 4 – Quy tắc IQR: giá trị nằm ngoài ``[Q1 - k·IQR, Q3 + k·IQR]``.

    Hàm **chỉ đánh dấu**, không xóa: trong dữ liệu bán lẻ, doanh thu rất cao thường
    là khách hàng giá trị cao chứ không phải lỗi nhập liệu.
    """
    s = pd.to_numeric(df[column], errors="coerce").dropna()
    q1 = float(s.quantile(0.25))
    q3 = float(s.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    mask = (s < lower) | (s > upper)
    return OutlierReport(
        column=column,
        q1=q1,
        q3=q3,
        iqr=iqr,
        lower_bound=lower,
        upper_bound=upper,
        n_outliers=int(mask.sum()),
        total=int(len(s)),
    )


def flag_outliers(
    df: pd.DataFrame,
    columns: tuple[str, ...] = ("unit_price", "amount"),
    multiplier: float = 1.5,
) -> tuple[pd.DataFrame, list[OutlierReport]]:
    """Thêm cột ``is_outlier_<col>`` đánh dấu giá trị ngoài khoảng IQR."""
    df = df.copy()
    reports: list[OutlierReport] = []
    for col in columns:
        if col not in df.columns:
            continue
        rep = detect_outliers_iqr(df, col, multiplier)
        s = pd.to_numeric(df[col], errors="coerce")
        df[f"is_outlier_{col}"] = ((s < rep.lower_bound) | (s > rep.upper_bound)).fillna(False)
        reports.append(rep)
    return df, reports


# ── Binning (Slide 1.1) ──────────────────────────────────────────────────────
def add_binning(
    df: pd.DataFrame,
    columns: tuple[str, ...] = ("quantity", "unit_price"),
    n_bins: int = 5,
    method: str = "quantile",  # "quantile" (đẳng phân vị) | "uniform" (đẳng khoảng)
) -> tuple[pd.DataFrame, list[str]]:
    """Slide 1.1 – Rời rác (discretization) bằng equal-width hoặc equal-depth.

    ``method="uniform"``  → equal-width  (khoảng đều nhau)
    ``method="quantile"`` → equal-depth  (số lượng mỗi bin đều nhau)
    """
    df = df.copy()
    log: list[str] = []
    for col in columns:
        if col not in df.columns:
            continue
        if method == "uniform":
            binned, _ = pd.cut(df[col], bins=n_bins, labels=False, retbins=True)
            kind = "equal-width"
        else:
            try:
                binned, _ = pd.qcut(
                    df[col], q=n_bins, labels=False, duplicates="drop", retbins=True
                )
                kind = "equal-depth"
            except ValueError:
                binned, _ = pd.cut(df[col], bins=n_bins, labels=False, retbins=True)
                kind = "equal-width"
        df[f"bin_{col}"] = binned.astype("Int64")
        log.append(f"{col}: binning {kind}, {n_bins} bins")
    return df, log


# ── Chuẩn hóa (Slide 1.1) ───────────────────────────────────────────────────
def min_max_scale(s: pd.Series) -> pd.Series:
    """Slide 1.1 – Min-Max Scaling: (x - min) / (max - min)."""
    lo, hi = s.min(), s.max()
    if hi == lo:
        return pd.Series(0.0, index=s.index)
    return (s - lo) / (hi - lo)


def zscore_scale(s: pd.Series) -> pd.Series:
    """Slide 1.1 – Z-score Normalization: (x - μ) / σ."""
    mu, sigma = s.mean(), s.std(ddof=0)
    if sigma == 0:
        return pd.Series(0.0, index=s.index)
    return (s - mu) / sigma


def log_transform(s: pd.Series) -> pd.Series:
    """log(1 + x) – nén phân phối lệch phải (F, M trong RFM)."""
    return np.log1p(pd.to_numeric(s, errors="coerce").clip(lower=0))


# ── Thống kê mô tả (Slide 4) ─────────────────────────────────────────────────
def describe_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Slide 4 – Mean / Median / Mode / Range / Variance / Std."""
    numeric = df.select_dtypes(include="number")
    desc = numeric.describe().T
    desc["mode"] = numeric.mode().iloc[0]
    desc["range"] = numeric.max() - numeric.min()
    desc["variance"] = numeric.var(ddof=0)
    desc["std"] = numeric.std(ddof=0)
    desc["skewness"] = numeric.skew()
    desc = desc.rename(columns={"count": "n", "50%": "median"})
    return desc[
        ["n", "mean", "median", "mode", "min", "max", "range", "variance", "std", "skewness"]
    ]


def value_counts(df: pd.DataFrame, column: str, top: int | None = None) -> pd.DataFrame:
    """Slide 2.2 – ``value_counts()`` kèm tỷ lệ và doanh thu."""
    g = df.groupby(column).agg(
        n_rows=("amount", "size"),
        n_orders=("order_id", "nunique"),
        revenue=("amount", "sum"),
    )
    g["share_rows"] = g["n_rows"] / g["n_rows"].sum()
    g = g.sort_values("n_rows", ascending=False)
    return g.head(top) if top else g


def pearson_correlation(df: pd.DataFrame, col_x: str, col_y: str) -> dict[str, float | str]:
    """Slide 1.1 – Hệ số tương quan Pearson r."""
    x = pd.to_numeric(df[col_x], errors="coerce")
    y = pd.to_numeric(df[col_y], errors="coerce")
    r = float(x.corr(y))
    return {
        "col_x": col_x,
        "col_y": col_y,
        "pearson_r": r,
        "r_squared": r**2,
        "interpretation": (
            "Tương quan dương rất mạnh" if r >= 0.9
            else "Tương quan dương mạnh" if r >= 0.7
            else "Tương quan dương trung bình" if r >= 0.4
            else "Tương quan dương yếu" if r >= 0.1
            else "Tương quan âm" if r <= -0.1
            else "Không tương quan đáng kể"
        ),
    }
