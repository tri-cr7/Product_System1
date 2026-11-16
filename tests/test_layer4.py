"""Test Tầng 4 – gợi ý đa tầng + đánh giá Top-K."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.config import RecommenderConfig
from src.evaluation.metrics import (
    build_history,
    build_relevance,
    evaluate_all_strategies,
    evaluate_recommendations,
    split_by_time,
)
from src.layers import layer4_recommender as l4


@pytest.fixture(scope="module")
def toy_setup():
    """Bộ dữ liệu giả lập: 3 sản phẩm, 2 phân khúc, khách ấm + khách lạnh."""
    rows = []
    rng = np.random.default_rng(42)
    for i in range(120):
        cust = f"k{i % 20}"
        seg = "A1" if i % 2 == 0 else "B1"
        items = ["A", "B"] if i % 3 == 0 else (["A"] if i % 3 == 1 else ["C"])
        for it in items:
            rows.append({
                "order_id": f"o{i}", "customer_id": cust, "segment_code": seg,
                "segment_desc": seg, "item_code": it, "item_name": f"Item {it}",
                "group_code": "G1" if it in ("A", "B") else "G2",
                "group_name": "G1" if it in ("A", "B") else "G2",
                "amount": 100, "quantity": 1, "unit_price": 100,
                "order_time": pd.Timestamp("2022-06-01") + pd.Timedelta(days=i % 30),
            })
    df = pd.DataFrame(rows)
    segs = df.groupby("customer_id")["segment_code"].first().to_dict()
    idx = l4.build_item_index(df, RecommenderConfig())
    return df, segs, idx


class TestTextCleaning:
    def test_lowercase_and_strip_accents(self):
        assert l4.clean_text("Trà Gừng") == "trà gừng"

    def test_removes_numbers(self):
        assert "10" not in l4.clean_text("Set 10 gói")

    def test_removes_stopwords(self):
        out = l4.clean_text("Gói trà của khách")
        assert "của" not in out.split()

    def test_handles_empty(self):
        assert l4.clean_text("") == ""
        assert l4.clean_text(None) == ""


class TestItemIndex:
    def test_similarity_matrix_shape(self, toy_setup):
        _, _, idx = toy_setup
        assert idx.similarity.shape == (len(idx.codes), len(idx.codes))

    def test_diagonal_is_negative(self, toy_setup):
        _, _, idx = toy_setup
        assert np.all(np.diag(idx.similarity) == -1.0)

    def test_most_similar_excludes_self(self, toy_setup):
        _, _, idx = toy_setup
        code = idx.codes[0]
        sims = idx.most_similar(code, top_n=2)
        assert all(c != code for c, _ in sims)


class TestStrategies:
    def test_global_popularity(self, toy_setup):
        df, _, _ = toy_setup
        recs = l4.strategy_global_popularity(df, list(df["customer_id"].unique()))
        assert len(recs.recommendations) == df["customer_id"].nunique()

    def test_segment_popularity_uses_segment(self, toy_setup):
        df, segs, _ = toy_setup
        custs = sorted(df["customer_id"].unique())
        recs = l4.strategy_segment_popularity(df, custs, segs)
        for c in custs:
            assert len(recs.recommendations[c]) > 0

    def test_normalize_scores_scales_to_unit(self, toy_setup):
        df, segs, _ = toy_setup
        custs = sorted(df["customer_id"].unique())
        raw = l4.strategy_segment_lift(df, custs, segs)
        norm = l4.normalize_scores(raw)
        max_val = max(v for s in norm.scores.values() for v in s.values())
        assert max_val == pytest.approx(1.0, abs=1e-6)

    def test_random_baseline_deterministic(self, toy_setup):
        df, _, _ = toy_setup
        custs = sorted(df["customer_id"].unique())
        a = l4.strategy_random(df, custs, seed=7)
        b = l4.strategy_random(df, custs, seed=7)
        assert a.recommendations == b.recommendations

    def test_content_based_no_history_returns_empty(self, toy_setup):
        df, _, idx = toy_setup
        recs = l4.strategy_content_based(df, ["khach_moi"], idx)
        assert recs.recommendations["khach_moi"] == []


class TestMultiLayer:
    def test_warm_customer_uses_branch_a(self, toy_setup):
        df, segs, idx = toy_setup
        custs = sorted(df["customer_id"].unique())
        multi = l4.MultiLayerRecommender(df, idx, RecommenderConfig(), segs,
                                        all_customers=custs)
        warm = multi.recommend(custs[0])
        assert warm.customer_type == "warm"
        assert warm.branch_used == "A"

    def test_cold_customer_uses_branch_b(self, toy_setup):
        df, segs, idx = toy_setup
        custs = sorted(df["customer_id"].unique())
        multi = l4.MultiLayerRecommender(df, idx, RecommenderConfig(), segs,
                                        all_customers=custs + ["khach_moi"])
        cold = multi.recommend("khach_moi")
        assert cold.customer_type == "cold"
        assert cold.branch_used == "B"
        assert len(cold.recommendations) > 0, "nhánh B phải có gợi ý cho khách lạnh"

    def test_never_recommends_owned_items(self, toy_setup):
        df, segs, idx = toy_setup
        custs = sorted(df["customer_id"].unique())
        multi = l4.MultiLayerRecommender(df, idx, RecommenderConfig(), segs,
                                        all_customers=custs)
        for c in custs:
            res = multi.recommend(c)
            owned = multi.history.get(c, set())
            rec_codes = {r.item_code for r in res.recommendations}
            assert not (rec_codes & owned)

    def test_respects_top_k(self, toy_setup):
        df, segs, idx = toy_setup
        custs = sorted(df["customer_id"].unique())
        multi = l4.MultiLayerRecommender(
            df, idx, RecommenderConfig(top_k=2), segs, all_customers=custs
        )
        assert len(multi.recommend(custs[0]).recommendations) <= 2

    def test_recommendations_have_reasons(self, toy_setup):
        df, segs, idx = toy_setup
        custs = sorted(df["customer_id"].unique())
        multi = l4.MultiLayerRecommender(df, idx, RecommenderConfig(), segs,
                                        all_customers=custs)
        res = multi.recommend(custs[0])
        assert all(r.reason for r in res.recommendations)
        assert all(r.branch in {"A", "B", "C"} for r in res.recommendations)

    def test_to_dict_serializable(self, toy_setup):
        import json

        df, segs, idx = toy_setup
        custs = sorted(df["customer_id"].unique())
        multi = l4.MultiLayerRecommender(df, idx, RecommenderConfig(), segs,
                                        all_customers=custs)
        json.dumps(multi.recommend(custs[0]).to_dict())


class TestEvaluation:
    def test_perfect_recommendations(self):
        recs = {"c1": ["a", "b", "c", "d", "e"]}
        relevant = {"c1": {"a", "b"}}
        res = evaluate_recommendations(recs, relevant, k=5, strategy="perfect")
        assert res.precision_at_k == pytest.approx(0.4)
        assert res.recall_at_k == pytest.approx(1.0)
        assert res.hit_rate_at_k == pytest.approx(1.0)
        assert res.ndcg_at_k == pytest.approx(1.0)

    def test_no_overlap(self):
        recs = {"c1": ["x", "y", "z", "w", "v"]}
        relevant = {"c1": {"a", "b"}}
        res = evaluate_recommendations(recs, relevant, k=5)
        assert res.precision_at_k == 0.0
        assert res.hit_rate_at_k == 0.0
        assert res.ndcg_at_k == 0.0

    def test_ndcg_penalises_lower_position(self):
        relevant = {"c1": {"b"}}
        top = evaluate_recommendations({"c1": ["b", "a", "c", "d", "e"]}, relevant, k=5)
        bottom = evaluate_recommendations({"c1": ["a", "c", "d", "e", "b"]}, relevant, k=5)
        assert top.ndcg_at_k > bottom.ndcg_at_k

    def test_split_by_time(self, raw_df):
        train, test = split_by_time(raw_df, "2022-10-01")
        assert train["order_time"].max() < pd.Timestamp("2022-10-01")
        assert test["order_time"].min() >= pd.Timestamp("2022-10-01")
        assert len(train) + len(test) == len(raw_df)

    def test_build_relevance_excludes_train_items(self, small_df):
        train, test = split_by_time(small_df, "2022-10-01")
        hist = build_history(train)
        rel = build_relevance(test, hist)
        for cust, items in rel.items():
            assert not (items & hist.get(cust, set()))

    def test_evaluate_all_strategies_sorted(self):
        recs = {
            "good": {"c1": ["a", "b"]},
            "bad": {"c1": ["x", "y"]},
        }
        relevant = {"c1": {"a", "b"}}
        out = evaluate_all_strategies(recs, relevant, k=2)
        assert out.iloc[0]["strategy"] == "good"
        assert len(out) == 2
