"""Tầng 1 – Kiểm định chi-square (Slide 1.1).

Công thức: ``χ² = Σ (O − E)² / E``, bậc tự do ``dof = (r−1)(c−1)``.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency


@dataclass
class ChiSquareResult:
    """Kết quả kiểm định chi-square trên bảng phân phối chéo."""

    name: str
    chi2: float
    dof: int
    p_value: float
    cramers_v: float
    contingency: pd.DataFrame
    min_expected: float
    n_expected_below_5: int
    significant: bool
    alpha: float

    @property
    def effect_strength(self) -> str:
        """Phân loại cường độ hiệu ứng theo Cramér's V (Cohen, 1988)."""
        v = self.cramers_v
        if v < 0.1:
            return "Rất yếu"
        if v < 0.3:
            return "Yếu"
        if v < 0.5:
            return "Trung bình"
        return "Mạnh"

    @property
    def valid(self) -> bool:
        """Điều kiện dùng được kiểm định chi-square: E ≥ 5 ở mọi ô."""
        return self.n_expected_below_5 == 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "chi2": self.chi2,
            "dof": self.dof,
            "p_value": self.p_value,
            "cramers_v": self.cramers_v,
            "effect_strength": self.effect_strength,
            "significant": self.significant,
            "min_expected": self.min_expected,
            "n_expected_below_5": self.n_expected_below_5,
            "valid": self.valid,
            "alpha": self.alpha,
        }


def chi_square_test(
    df: pd.DataFrame,
    row_col: str,
    col_col: str,
    alpha: float = 0.05,
    name: str | None = None,
) -> ChiSquareResult:
    """Kiểm định độc lập giữa hai biến phân loại (Slide 1.1).

    Parameters
    ----------
    df:
        Dữ liệu chi tiết.
    row_col, col_col:
        Tên hai cột phân loại.
    alpha:
        Ngưỡng ý nghĩa thống kê.

    Returns
    -------
    ChiSquareResult
        Kèm bảng phân phối chéo và chỉ số Cramér's V để đánh giá **hiệu ứng thực tế**
        (điểm phân biệt "có ý nghĩa thống kê" với "có ý nghĩa kinh doanh").
    """
    table = pd.crosstab(df[row_col], df[col_col])
    chi2, p_value, dof, expected = chi2_contingency(table.values)

    n = table.values.sum()
    min_dim = min(table.shape) - 1
    cramers_v = float(np.sqrt(chi2 / (n * min_dim))) if min_dim > 0 else float("nan")

    return ChiSquareResult(
        name=name or f"{row_col} × {col_col}",
        chi2=float(chi2),
        dof=int(dof),
        p_value=float(p_value),
        cramers_v=cramers_v,
        contingency=table,
        min_expected=float(expected.min()),
        n_expected_below_5=int((expected < 5).sum()),
        significant=bool(p_value < alpha),
        alpha=alpha,
    )


def chi_square_2x2(
    n11: int,
    n10: int,
    n01: int,
    n00: int,
    alpha: float = 0.05,
    name: str = "",
) -> ChiSquareResult:
    """Kiểm định chi-square trên bảng 2×2 — *áp dụng mới* công thức Slide 1.1.

    Dùng để kiểm định một luật kết hợp: ``n11`` = số đơn có **cả** A và B,
    ``n10`` = chỉ A, ``n01`` = chỉ B, ``n00`` = không có sản phẩm nào.
    """
    table = pd.DataFrame(
        [[n11, n10], [n01, n00]],
        index=["có B", "không B"],
        columns=["có A", "không A"],
    )
    chi2, p_value, dof, expected = chi2_contingency(table.values)

    n = table.values.sum()
    cramers_v = float(np.sqrt(chi2 / n))  # dof = 1
    return ChiSquareResult(
        name=name or "bảng 2×2",
        chi2=float(chi2),
        dof=int(dof),
        p_value=float(p_value),
        cramers_v=cramers_v,
        contingency=table,
        min_expected=float(expected.min()),
        n_expected_below_5=int((expected < 5).sum()),
        significant=bool(p_value < alpha),
        alpha=alpha,
    )
