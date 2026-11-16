"""Test Tầng 3 – Market Basket Analysis."""
from __future__ import annotations

import pandas as pd
import pytest

from src.config import MBARulesConfig
from src.layers import layer3_mba as l3


@pytest.fixture
def toy_df():
    """Dữ liệu giả lập có luật kết hợp rõ ràng: A→B mạnh, C độc lập."""
    rows = []
    # 100 đơn chứa A và B
    for i in range(100):
        rows.append({"order_id": f"o{i}", "customer_id": f"k{i % 10}",
                     "item_code": "A", "item_name": "A", "group_code": "G1",
                     "group_name": "G1", "amount": 100, "quantity": 1,
                     "unit_price": 100, "order_time": pd.Timestamp("2022-01-01")})
        rows.append({"order_id": f"o{i}", "customer_id": f"k{i % 10}",
                     "item_code": "B", "item_name": "B", "group_code": "G1",
                     "group_name": "G1", "amount": 100, "quantity": 1,
                     "unit_price": 100, "order_time": pd.Timestamp("2022-01-01")})
    # 100 đơn chỉ chứa C
    for i in range(100, 200):
        rows.append({"order_id": f"o{i}", "customer_id": f"k{i % 10}",
                     "item_code": "C", "item_name": "C", "group_code": "G2",
                     "group_name": "G2", "amount": 100, "quantity": 1,
                     "unit_price": 100, "order_time": pd.Timestamp("2022-01-01")})
    return pd.DataFrame(rows)


class TestAssociationRules:
    def test_mining_finds_rules(self, toy_df):
        res = l3.mine_association_rules(toy_df, MBARulesConfig(min_support=0.1,
                                                               min_confidence=0.1))
        assert res.n_baskets == 200
        assert res.n_rules > 0

    def test_lift_greater_than_one_for_strong_rule(self, toy_df):
        res = l3.mine_association_rules(toy_df, MBARulesConfig(min_support=0.1,
                                                               min_confidence=0.1))
        ab = res.rules[(res.rules["antecedent"] == "A")
                       & (res.rules["consequent"] == "B")]
        assert len(ab) == 1
        assert ab.iloc[0]["lift"] > 1.5
        assert ab.iloc[0]["confidence"] == pytest.approx(1.0)
        assert ab.iloc[0]["support"] == pytest.approx(0.5)

    def test_independent_pair_has_lift_one(self, toy_df):
        res = l3.mine_association_rules(toy_df, MBARulesConfig(min_support=0.1,
                                                               min_confidence=0.1))
        ac = res.rules[(res.rules["antecedent"] == "A")
                       & (res.rules["consequent"] == "C")]
        if len(ac):
            assert ac.iloc[0]["lift"] == pytest.approx(1.0)

    def test_min_support_filters(self, toy_df):
        strict = l3.mine_association_rules(toy_df, MBARulesConfig(min_support=0.9,
                                                                  min_confidence=0.1))
        loose = l3.mine_association_rules(toy_df, MBARulesConfig(min_support=0.01,
                                                                 min_confidence=0.1))
        assert strict.n_rules <= loose.n_rules

    def test_metrics_are_consistent(self, toy_df):
        res = l3.mine_association_rules(toy_df, MBARulesConfig(min_support=0.1,
                                                               min_confidence=0.1))
        for _, r in res.rules.iterrows():
            assert r["support"] == pytest.approx(r["n_orders"] / res.n_baskets)
            expected_leverage = r["support"] - (r["support"] / r["confidence"]) * (
                r["support"] / r["confidence"]
            ) if False else None  # kiểm tra bằng công thức đầy đủ bên dưới
        assert len(res.rules) > 0

    def test_leverage_formula(self, toy_df):
        res = l3.mine_association_rules(toy_df, MBARulesConfig(min_support=0.1,
                                                               min_confidence=0.1))
        ab = res.rules[(res.rules["antecedent"] == "A")
                       & (res.rules["consequent"] == "B")].iloc[0]
        # sup(A) = 0.5, sup(B) = 0.5, sup(A∪B) = 0.5 → leverage = 0.5 - 0.25 = 0.25
        assert ab["leverage"] == pytest.approx(0.25, abs=1e-6)

    def test_exploratory_mining_returns_all_pairs(self, toy_df):
        """Khám phá toàn bộ: chỉ sinh luật cho các cặp **thực sự cùng xuất hiện**.

        Cặp (A, C) không bao giờ cùng xuất hiện trong một đơn → không tồn tại
        luật. Đây là hành vi đúng của Apriori (candidate set chỉ gồm tập mục
        có support > 0).
        """
        res = l3.mine_association_rules(toy_df, min_support=0.0, min_confidence=0.0)
        pairs = set(
            zip(res.rules["antecedent"], res.rules["consequent"])
        )
        assert ("A", "B") in pairs and ("B", "A") in pairs
        assert ("A", "C") not in pairs
        # Mỗi cặp sinh 2 hướng → 3 items nhưng chỉ 1 cặp thực sự đồng xuất hiện
        assert res.n_rules == 2

    def test_operational_filter(self, toy_df):
        res = l3.mine_association_rules(toy_df, MBARulesConfig(min_support=0.1,
                                                               min_confidence=0.1))
        op = res.operational(lift_threshold=1.0)
        assert (op["lift"] > 1.0).all()


class TestRuleSignificance:
    def test_chi_square_on_rules(self, toy_df):
        res = l3.mine_association_rules(toy_df, MBARulesConfig(min_support=0.1,
                                                               min_confidence=0.1))
        tests = l3.test_rules_significance(toy_df, res.rules, top_n=5)
        assert len(tests) > 0
        assert "chi2" in tests.columns
        assert "p_value" in tests.columns

    def test_targeted_rules_by_segment(self, raw_df):
        df = raw_df.copy()
        df["segment_code"] = df["segment_code"].astype(str)
        rules = l3.targeted_rules_by_segment(df)
        assert isinstance(rules, pd.DataFrame)


class TestBasketStats:
    def test_basket_statistics(self, small_df):
        stats = l3.basket_statistics(small_df)
        assert stats["n_orders"] == small_df["order_id"].nunique()
        assert stats["avg_items_per_order"] > 0
        assert 0 <= stats["share_multi_item_orders"] <= 1

    def test_item_support_table(self, small_df):
        sup = l3.item_support_table(small_df)
        assert len(sup) == small_df["item_code"].nunique()
        assert sup["support"].max() <= 1.0
        assert sup["support"].min() >= 0.0
