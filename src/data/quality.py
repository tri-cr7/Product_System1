"""Kiểm định chất lượng dữ liệu – Slide 1.1 (Data Cleaning).

Mỗi kiểm tra trả về một :class:`QualityCheck` để có thể hiển thị trong báo cáo
và trong API mà không phải đoán xét thủ công.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class QualityCheck:
    """Kết quả một phép kiểm tra chất lượng."""

    name: str
    passed: bool
    detail: str
    n_affected: int = 0
    severity: str = "info"  # "info" | "warning" | "error"
    metrics: dict[str, Any] = field(default_factory=dict)


def check_duplicates(df: pd.DataFrame) -> QualityCheck:
    n = int(df.duplicated().sum())
    return QualityCheck(
        name="Dòng trùng lặp",
        passed=n == 0,
        detail="Không có dòng trùng lặp" if n == 0 else f"{n} dòng trùng lặp",
        n_affected=n,
        severity="info" if n == 0 else "warning",
        metrics={"n_duplicates": n},
    )


def check_missing(df: pd.DataFrame, columns: list[str] | None = None) -> list[QualityCheck]:
    cols = columns or list(df.columns)
    out: list[QualityCheck] = []
    for col in cols:
        n = int(df[col].isna().sum())
        out.append(
            QualityCheck(
                name=f"Giá trị rỗng – {col}",
                passed=n == 0,
                detail=(
                    "Không có giá trị rỗng"
                    if n == 0
                    else f"{n} giá trị rỗng ({n / len(df):.2%})"
                ),
                n_affected=n,
                severity="info" if n == 0 else "warning",
                metrics={"column": col, "n_missing": n, "ratio": n / max(len(df), 1)},
            )
        )
    return out


def check_amount_consistency(df: pd.DataFrame) -> QualityCheck:
    """Kiểm tra amount == quantity × unit_price."""
    expected = df["quantity"] * df["unit_price"]
    n_bad = int((df["amount"] != expected).sum())
    return QualityCheck(
        name="Thành tiền = SL × Đơn giá",
        passed=n_bad == 0,
        detail=(
            "100% khớp" if n_bad == 0 else f"{n_bad} dòng sai lệch"
        ),
        n_affected=n_bad,
        severity="info" if n_bad == 0 else "error",
        metrics={"n_mismatch": n_bad},
    )


def check_non_positive_price(df: pd.DataFrame) -> QualityCheck:
    n = int((df["unit_price"] <= 0).sum())
    return QualityCheck(
        name="Đơn giá không dương",
        passed=n == 0,
        detail="Không có giá ≤ 0" if n == 0 else f"{n} dòng có đơn giá ≤ 0",
        n_affected=n,
        severity="info" if n == 0 else "error",
        metrics={"n_non_positive": n},
    )


def check_order_customer_consistency(df: pd.DataFrame) -> QualityCheck:
    """Mỗi đơn hàng phải thuộc đúng một khách hàng."""
    per_order = df.groupby("order_id")["customer_id"].nunique()
    n_bad = int((per_order > 1).sum())
    return QualityCheck(
        name="Mỗi đơn thuộc 1 khách duy nhất",
        passed=n_bad == 0,
        detail="Toàn bộ đơn hàng nhất quán" if n_bad == 0 else f"{n_bad} đơn thuộc >1 khách",
        n_affected=n_bad,
        severity="info" if n_bad == 0 else "error",
        metrics={"n_inconsistent_orders": n_bad},
    )


def check_single_segment_per_customer(df: pd.DataFrame) -> QualityCheck:
    per_cust = df.groupby("customer_id")["segment_code"].nunique()
    n_bad = int((per_cust > 1).sum())
    return QualityCheck(
        name="Mỗi khách có 1 Mã PKKH",
        passed=n_bad == 0,
        detail="Nhãn phân khúc nhất quán theo khách"
        if n_bad == 0
        else f"{n_bad} khách có nhiều nhãn",
        n_affected=n_bad,
        severity="info" if n_bad == 0 else "warning",
        metrics={"n_inconsistent_customers": n_bad},
    )


def check_item_single_group(df: pd.DataFrame) -> QualityCheck:
    per_item = df.groupby("item_code")["group_code"].nunique()
    n_bad = int((per_item > 1).sum())
    return QualityCheck(
        name="Mỗi mặt hàng thuộc 1 nhóm hàng",
        passed=n_bad == 0,
        detail="Phân loại nhóm hàng nhất quán"
        if n_bad == 0
        else f"{n_bad} mã hàng thuộc nhiều nhóm",
        n_affected=n_bad,
        severity="info" if n_bad == 0 else "warning",
        metrics={"n_inconsistent_items": n_bad},
    )


def run_all_checks(df: pd.DataFrame) -> list[QualityCheck]:
    """Chạy toàn bộ kiểm tra chất lượng."""
    checks: list[QualityCheck] = [check_duplicates(df)]
    checks.extend(check_missing(df))
    checks.append(check_amount_consistency(df))
    checks.append(check_non_positive_price(df))
    checks.append(check_order_customer_consistency(df))
    checks.append(check_single_segment_per_customer(df))
    checks.append(check_item_single_group(df))
    return checks
