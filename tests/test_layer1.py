"""Test Tầng 1 – nạp dữ liệu, kiểm định chất lượng, tiền xử lý, thống kê."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.config import PreprocessConfig
from src.data.quality import (
    check_amount_consistency,
    check_duplicates,
    check_single_segment_per_customer,
    run_all_checks,
)
from src.layers import layer1_preprocessing as l1
from src.layers import layer1_statistics as l1s


class TestLoader:
    def test_columns_are_canonical(self, raw_df):
        assert "customer_id" in raw_df.columns
        assert "item_code" in raw_df.columns
        assert "amount" in raw_df.columns

    def test_dtypes(self, raw_df):
        assert pd.api.types.is_datetime64_any_dtype(raw_df["order_time"])
        assert pd.api.types.is_numeric_dtype(raw_df["amount"])
        assert pd.api.types.is_numeric_dtype(raw_df["quantity"])

    def test_no_missing_keys(self, raw_df):
        for col in ("order_id", "customer_id", "item_code", "group_code"):
            assert raw_df[col].isna().sum() == 0, f"{col} có giá trị rỗng"


class TestQuality:
    def test_amount_consistency(self, raw_df):
        res = check_amount_consistency(raw_df)
        assert res.passed, res.detail
        assert res.n_affected == 0

    def test_single_segment_per_customer(self, raw_df):
        assert check_single_segment_per_customer(raw_df).passed

    def test_duplicates_detected(self):
        df = pd.DataFrame({"a": [1, 1, 2]})
        assert check_duplicates(df).n_affected == 1

    def test_run_all_checks_returns_list(self, raw_df):
        checks = run_all_checks(raw_df)
        assert len(checks) >= 8
        assert all(hasattr(c, "passed") for c in checks)


class TestPreprocessing:
    def test_handle_missing_fills_only_display_columns(self, small_df):
        df = small_df.copy()
        df.loc[df.index[:5], "customer_name"] = None
        out, log = l1.handle_missing(df)
        assert out["customer_name"].isna().sum() == 0
        assert any("customer_name" in entry for entry in log)

    def test_drop_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2, 3]})
        out, removed = l1.drop_duplicates(df)
        assert removed == 1
        assert len(out) == 3

    def test_iqr_outlier_detection(self):
        s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 1000])
        df = pd.DataFrame({"v": s})
        rep = l1.detect_outliers_iqr(df, "v")
        assert rep.n_outliers >= 1
        assert rep.lower_bound < rep.q1 <= rep.q3 < rep.upper_bound

    def test_flag_outliers_adds_column(self, small_df):
        out, reports = l1.flag_outliers(small_df, ("amount",))
        assert "is_outlier_amount" in out.columns
        assert len(reports) == 1

    def test_binning(self, small_df):
        out, log = l1.add_binning(small_df, ("quantity",), n_bins=4)
        assert "bin_quantity" in out.columns
        assert out["bin_quantity"].notna().sum() > 0

    def test_min_max_scale(self):
        s = pd.Series([0.0, 5.0, 10.0])
        out = l1.min_max_scale(s)
        assert out.min() == 0.0 and out.max() == 1.0

    def test_zscore_scale(self):
        s = pd.Series([1.0, 2.0, 3.0])
        out = l1.zscore_scale(s)
        assert abs(out.mean()) < 1e-9
        assert abs(out.std(ddof=0) - 1.0) < 1e-9

    def test_log_transform(self):
        s = pd.Series([0.0, 9.0])
        np.testing.assert_allclose(l1.log_transform(s).values, [0.0, np.log(10)])

    def test_log_transform_handles_negative(self):
        out = l1.log_transform(pd.Series([-5.0, 9.0]))
        assert (out >= 0).all()

    def test_describe_numeric(self, small_df):
        desc = l1.describe_numeric(small_df)
        assert "mean" in desc.columns and "median" in desc.columns
        assert len(desc) > 0

    def test_pearson_correlation_perfect(self):
        df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [2, 4, 6, 8]})
        res = l1.pearson_correlation(df, "x", "y")
        assert res["pearson_r"] == pytest.approx(1.0)
        assert res["r_squared"] == pytest.approx(1.0)


class TestStatistics:
    def test_chi_square_detects_dependence(self):
        df = pd.DataFrame(
            {
                "a": ["x"] * 50 + ["y"] * 50,
                "b": ["p"] * 50 + ["q"] * 50,
            }
        )
        res = l1s.chi_square_test(df, "a", "b")
        assert res.significant
        assert res.cramers_v > 0.5

    def test_chi_square_detects_independence(self):
        rng = np.random.default_rng(42)
        df = pd.DataFrame(
            {
                "a": rng.choice(["x", "y"], 200),
                "b": rng.choice(["p", "q"], 200),
            }
        )
        res = l1s.chi_square_test(df, "a", "b")
        assert res.p_value > 0.05

    def test_chi_square_2x2(self):
        res = l1s.chi_square_2x2(30, 20, 25, 25, name="test")
        assert res.dof == 1
        assert 0.0 <= res.cramers_v <= 1.0

    def test_effect_strength_buckets(self):
        df = pd.DataFrame({"a": ["x"] * 60 + ["y"] * 40, "b": ["p"] * 60 + ["q"] * 40})
        res = l1s.chi_square_test(df, "a", "b")
        assert res.effect_strength in {"Rất yếu", "Yếu", "Trung bình", "Mạnh"}
