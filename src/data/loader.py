"""Tải và chuẩn hoá dữ liệu thô từ file Excel.

Slide 1.1 – Data Preparation: kiểm tra cấu trúc, đổi tên cột, ép kiểu dữ liệu.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..config import (
    CANONICAL_COLUMNS,
    DATA_FILE,
    RAW_COLUMNS,
    SHEET_NAME,
)


class DataSchemaError(ValueError):
    """Dữ liệu không khớp schema kỳ vọng."""


@dataclass
class LoadResult:
    """Kết quả nạp dữ liệu kèm nhật ký biến đổi."""

    frame: pd.DataFrame
    source: Path
    n_rows_raw: int
    transformations: list[str] = field(default_factory=list)

    @property
    def n_rows(self) -> int:
        return len(self.frame)


def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = dict(zip(RAW_COLUMNS, CANONICAL_COLUMNS))
    missing = [c for c in RAW_COLUMNS if c not in df.columns]
    if missing:
        raise DataSchemaError(f"Thiếu cột trong dữ liệu gốc: {missing}")
    return df.rename(columns=mapping)


def _coerce_types(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    log: list[str] = []
    df = df.copy()

    df["order_time"] = pd.to_datetime(df["order_time"], errors="coerce")
    n_bad_time = int(df["order_time"].isna().sum())
    if n_bad_time:
        log.append(f"order_time: ép kiểu datetime, {n_bad_time} giá trị không hợp lệ")
        df = df[df["order_time"].notna()].copy()

    for col in ("quantity", "unit_price", "amount"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
        n_bad = int(df[col].isna().sum())
        if n_bad:
            log.append(f"{col}: ép kiểu số, loại {n_bad} giá trị không hợp lệ")
            df = df[df[col].notna()].copy()

    for col in (
        "order_id",
        "customer_id",
        "customer_name",
        "segment_code",
        "segment_desc",
        "group_code",
        "group_name",
        "item_code",
        "item_name",
    ):
        df[col] = df[col].astype("string").str.strip()

    # Chuẩn hoá khoảng trắng thừa trong mã (có thể do copy/paste)
    for col in ("order_id", "customer_id", "segment_code", "group_code", "item_code"):
        before = df[col].nunique()
        df[col] = df[col].str.replace(r"\s+", "", regex=True)
        after = df[col].nunique()
        if before != after:
            log.append(f"{col}: loại bỏ khoảng trắng thừa ({before} → {after} mã)")

    df["quantity"] = df["quantity"].astype("int64")
    df["unit_price"] = df["unit_price"].astype("int64")
    df["amount"] = df["amount"].astype("int64")

    return df, log


def load_transactions(
    path: str | Path = DATA_FILE,
    sheet_name: str = SHEET_NAME,
) -> LoadResult:
    """Nạp bảng giao dịch và chuẩn hoá tên cột / kiểu dữ liệu.

    Raises
    ------
    DataSchemaError
        Nếu file không tồn tại hoặc thiếu cột bắt buộc.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file dữ liệu: {path}")

    raw = pd.read_excel(path, sheet_name=sheet_name)
    n_rows_raw = len(raw)

    df = _rename_columns(raw)
    df, log = _coerce_types(df)
    log.insert(0, f"Đổi tên {len(RAW_COLUMNS)} cột sang tên chuẩn hoá")

    df = df.reset_index(drop=True)
    return LoadResult(frame=df, source=path, n_rows_raw=n_rows_raw, transformations=log)
