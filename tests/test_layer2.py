"""Test Tầng 2 – RFM, K-Means, Elbow, Silhouette, Confusion Matrix."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.config import ClusterConfig, RFMConfig
from src.layers import layer2_clustering as l2


class TestRFM:
    def test_compute_rfm_shape(self, small_df):
        rfm = l2.compute_rfm(small_df)
        assert rfm.n_customers == small_df["customer_id"].nunique()
        assert {"recency", "frequency", "monetary"}.issubset(rfm.frame.columns)

    def test_rfm_values_consistent(self, small_df):
        rfm = l2.compute_rfm(small_df)
        row = rfm.frame.iloc[0]
        cid = row["customer_id"]
        sub = small_df[small_df["customer_id"] == cid]
        assert row["frequency"] == sub["order_id"].nunique()
        assert row["monetary"] == sub["amount"].sum()

    def test_log_transform_applied(self, small_df):
        rfm = l2.compute_rfm(small_df, RFMConfig(log_transform=True))
        assert "log_frequency" in rfm.frame.columns

    def test_minmax_scaler(self, small_df):
        rfm = l2.compute_rfm(small_df, RFMConfig(scaler="minmax"))
        for col in rfm.feature_columns:
            assert rfm.frame[col].max() <= 1.0 + 1e-9

    def test_rfm_labels(self, small_df):
        rfm = l2.compute_rfm(small_df)
        labels = l2.rfm_segment_labels(rfm.frame)
        assert len(labels) == len(rfm.frame)
        assert labels.notna().all()


class TestKMeans:
    def test_elbow_curve(self, small_df):
        rfm = l2.compute_rfm(small_df)
        res = l2.run_kmeans(rfm, ClusterConfig(k_range=(2, 6), selected_k=3))
        assert len(res.elbow.k_values) == 5
        # WCSS phải giảm dần khi K tăng
        assert all(
            res.elbow.wcss[i] > res.elbow.wcss[i + 1] for i in range(len(res.elbow.wcss) - 1)
        )
        # Silhouette nằm trong [-1, 1]
        assert all(-1 <= s <= 1 for s in res.elbow.silhouette)

    def test_cluster_labels_cover_all_customers(self, small_df):
        rfm = l2.compute_rfm(small_df)
        res = l2.run_kmeans(rfm, ClusterConfig(k_range=(2, 5), selected_k=3))
        assert len(res.labels) == rfm.n_customers
        assert set(res.labels.unique()) == {"C0", "C1", "C2"}

    def test_cluster_sizes_sum(self, small_df):
        rfm = l2.compute_rfm(small_df)
        res = l2.run_kmeans(rfm, ClusterConfig(k_range=(2, 5), selected_k=3))
        assert sum(res.sizes.values()) == rfm.n_customers

    def test_comparison_generated(self, small_df):
        rfm = l2.compute_rfm(small_df)
        res = l2.run_kmeans(rfm, ClusterConfig(k_range=(2, 5), selected_k=3))
        assert res.comparison is not None
        assert 0.0 <= res.comparison["purity"] <= 1.0
        assert "confusion_matrix" in res.comparison

    def test_cluster_profile(self, small_df):
        rfm = l2.compute_rfm(small_df)
        res = l2.run_kmeans(rfm, ClusterConfig(k_range=(2, 5), selected_k=3))
        prof = l2.cluster_profile(rfm.frame, res.labels)
        assert len(prof) == 3
        assert prof["n_customers"].sum() == rfm.n_customers

    def test_evaluate_against_segments_perfect_match(self):
        y = pd.Series(["a", "a", "b", "b", "c", "c"] * 5)
        res = l2.evaluate_against_segments(y, y, n_classes_true=3)
        assert res["purity"] == pytest.approx(1.0)
        assert res["accuracy_optimal"] == pytest.approx(1.0)


class TestSilhouette:
    def test_well_separated_clusters_have_high_silhouette(self):
        rng = np.random.default_rng(0)
        df = pd.DataFrame(
            {
                "customer_id": [f"c{i}" for i in range(300)],
                "recency": np.concatenate([rng.normal(0, 1, 100), rng.normal(50, 1, 100),
                                           rng.normal(100, 1, 100)]),
                "frequency": np.concatenate([rng.normal(0, 1, 100), rng.normal(50, 1, 100),
                                             rng.normal(100, 1, 100)]),
                "monetary": np.concatenate([rng.normal(0, 1, 100), rng.normal(50, 1, 100),
                                            rng.normal(100, 1, 100)]),
                "customer_segment": ["s1"] * 100 + ["s2"] * 100 + ["s3"] * 100,
            }
        )
        rfm = l2.RFMResult(frame=df, reference_date=pd.Timestamp("2022-01-01"),
                           feature_columns=["recency", "frequency", "monetary"])
        res = l2.run_kmeans(rfm, ClusterConfig(k_range=(2, 5), selected_k=3))
        assert res.silhouette > 0.9
