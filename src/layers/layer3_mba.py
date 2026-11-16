"""Tầng 3 – Khai phá luật kết hợp (Market Basket Analysis).

Các đại lượng:

* **Support**:  ``sup(X) = count(X) / N``
* **Confidence**: ``conf(X→Y) = sup(X∪Y) / sup(X)``
* **Lift**:  ``lift(X→Y) = sup(X∪Y) / (sup(X)·sup(Y))``  — ``> 1`` nghĩa là tương quan dương
* **Leverage**:  ``lev(X→Y) = sup(X∪Y) − sup(X)·sup(Y)``
* **Conviction**: ``conv = (1 − sup(Y)) / (1 − conf(X→Y))``

Luật được kiểm định thêm bằng **chi-square 2×2** (Slide 1.1 áp dụng mới).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
import pandas as pd

from ..config import MBARulesConfig
from .layer1_statistics import chi_square_2x2


@dataclass
class AssociationRules:
    """Tập luật kết hợp đã khai phá."""

    rules: pd.DataFrame
    n_baskets: int
    notes: list[str] = field(default_factory=list)

    @property
    def n_rules(self) -> int:
        return len(self.rules)

    def operational(self, lift_threshold: float = 1.0, min_support: float | None = None):
        """Các luật **đủ điều kiện đưa vào vận hành** (lift > 1 và support đủ lớn)."""
        df = self.rules
        if min_support is not None:
            df = df[df["support"] >= min_support]
        return df[df["lift"] > lift_threshold].reset_index(drop=True)


def _item_sets(baskets, max_len: int):
    """Đếm tần suất các tập mục có độ dài 1..max_len (phần "đếm" của Apriori)."""
    counts = {k: {} for k in range(1, max_len + 1)}
    for basket in baskets:
        items = sorted(basket)
        for size in range(1, min(max_len, len(items)) + 1):
            for combo in combinations(items, size):
                fs = frozenset(combo)
                counts[size][fs] = counts[size].get(fs, 0) + 1
    return counts


def mine_association_rules(
    df: pd.DataFrame,
    config: MBARulesConfig | None = None,
    min_support: float | None = None,
    min_confidence: float | None = None,
) -> AssociationRules:
    """Khai phá luật kết hợp theo nguyên lý Apriori.

    Parameters
    ----------
    df:
        Dữ liệu chi tiết giao dịch.
    config:
        Ngưỡng support / confidence và độ dài luật tối đa.
    min_support, min_confidence:
        Ghi đè ngưỡng cấu hình. Đặt ``min_support=0`` để liệt kê **toàn bộ** tổ hợp
        đôi (với 19 mặt hàng chỉ có 171 cặp) – cần thiết cho **khám phá phân phối Lift**:
        nếu lọc support trước, ta sẽ không nhìn thấy các luật có Lift > 1 nhưng
        support rất thấp, và kết luận "Apriori không sinh được luật mạnh" sẽ sai.
    """
    config = config or MBARulesConfig()
    notes: list[str] = []

    ms = config.min_support if min_support is None else min_support
    mc = config.min_confidence if min_confidence is None else min_confidence

    baskets = (
        df.groupby("order_id")["item_code"].apply(lambda s: frozenset(s.astype(str))).tolist()
    )
    n_baskets = len(baskets)
    if n_baskets == 0:
        return AssociationRules(
            rules=pd.DataFrame(), n_baskets=0, notes=["Không có đơn hàng nào"]
        )

    counts = _item_sets(baskets, config.max_itemset_length)

    item_support: dict[str, float] = {
        item: cnt / n_baskets for item, cnt in counts[1].items() for item in item
    }

    rows: list[dict] = []
    for size in range(2, config.max_itemset_length + 1):
        for itemset, cnt in counts[size].items():
            sup = cnt / n_baskets
            if sup < ms:
                continue
            items = sorted(itemset)
            for antecedent in items:
                for consequent in items:
                    if antecedent == consequent:
                        continue
                    conf = sup / item_support[antecedent]
                    if conf < mc:
                        continue
                    lift = conf / item_support[consequent]
                    leverage = sup - item_support[antecedent] * item_support[consequent]
                    denom = 1.0 - conf
                    conviction = (
                        (1.0 - item_support[consequent]) / denom if denom > 1e-12 else np.inf
                    )
                    rows.append(
                        {
                            "antecedent": antecedent,
                            "consequent": consequent,
                            "itemset_size": size,
                            "support": sup,
                            "confidence": conf,
                            "lift": lift,
                            "leverage": leverage,
                            "conviction": conviction,
                            "n_orders": cnt,
                        }
                    )

    rules = pd.DataFrame(rows)
    if not rules.empty:
        rules = rules.sort_values(["lift", "support"], ascending=[False, False]).reset_index(
            drop=True
        )

    notes.append(
        f"Khai phá trên {n_baskets:,} giỏ hàng, min_support={ms}, "
        f"min_confidence={mc}, độ dài luật ≤ {config.max_itemset_length}"
    )
    if not rules.empty:
        notes.append(f"Tìm được {len(rules)} luật")
        notes.append(
            f"Số luật có Lift > 1: {int((rules['lift'] > 1).sum())} "
            f"({(rules['lift'] > 1).mean():.1%})"
        )
    return AssociationRules(rules=rules, n_baskets=n_baskets, notes=notes)


def test_rules_significance(
    df: pd.DataFrame,
    rules: pd.DataFrame,
    top_n: int = 10,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Kiểm định chi-square 2×2 cho các luật có support cao nhất (Slide 1.1).

    Với mỗi luật ``A → B`` dựng bảng 2×2 gồm n11 (mua cả A và B), n10 (chỉ A),
    n01 (chỉ B) và n00 (không mua sản phẩm nào).
    """
    if rules.empty:
        return pd.DataFrame()

    orders = df.groupby("order_id")["item_code"].apply(
        lambda s: frozenset(s.astype(str))
    ).to_dict()

    rows = []
    for _, r in rules.head(top_n).iterrows():
        a, b = r["antecedent"], r["consequent"]
        n11 = n10 = n01 = n00 = 0
        for items in orders.values():
            has_a, has_b = a in items, b in items
            if has_a and has_b:
                n11 += 1
            elif has_a:
                n10 += 1
            elif has_b:
                n01 += 1
            else:
                n00 += 1
        res = chi_square_2x2(n11, n10, n01, n00, alpha=alpha, name=f"{a} × {b}")
        rows.append(
            {
                "antecedent": a,
                "consequent": b,
                "n11": n11,
                "n10": n10,
                "n01": n01,
                "n00": n00,
                "chi2": res.chi2,
                "dof": res.dof,
                "p_value": res.p_value,
                "cramers_v": res.cramers_v,
                "significant": res.significant,
                "lift": r["lift"],
                "support": r["support"],
                "direction": "tương quan dương" if r["lift"] > 1 else "tương quan âm",
            }
        )
    return pd.DataFrame(rows)


def targeted_rules_by_segment(
    df: pd.DataFrame,
    config: MBARulesConfig | None = None,
    min_support: float = 0.03,
) -> pd.DataFrame:
    """Khai phá luật **riêng theo từng phân khúc khách hàng**."""
    config = config or MBARulesConfig()
    rows = []
    for seg, g in df.groupby("segment_code"):
        sub = mine_association_rules(g, config)
        if sub.rules.empty:
            continue
        top = sub.rules[sub.rules["lift"] > 1].head(3)
        for _, r in top.iterrows():
            rows.append(
                {
                    "segment_code": seg,
                    "antecedent": r["antecedent"],
                    "consequent": r["consequent"],
                    "support": r["support"],
                    "confidence": r["confidence"],
                    "lift": r["lift"],
                    "n_baskets_segment": sub.n_baskets,
                }
            )
    return pd.DataFrame(rows)


def item_support_table(df: pd.DataFrame) -> pd.DataFrame:
    """Support của từng mặt hàng (tỷ lệ đơn hàng chứa sản phẩm)."""
    n_orders = df["order_id"].nunique()
    g = (
        df.groupby("item_code")
        .agg(
            n_orders=("order_id", "nunique"),
            n_rows=("amount", "size"),
            revenue=("amount", "sum"),
        )
        .reset_index()
    )
    g["support"] = g["n_orders"] / n_orders
    g["item_name"] = g["item_code"].map(df.groupby("item_code")["item_name"].first())
    g["group_name"] = g["item_code"].map(df.groupby("item_code")["group_name"].first())
    return g.sort_values("support", ascending=False).reset_index(drop=True)


def basket_statistics(df: pd.DataFrame) -> dict:
    """Thống kê mô tả cấu trúc giỏ hàng (Slide 4)."""
    n_items = df.groupby("order_id")["item_code"].nunique()
    groups = df.groupby("order_id")["group_code"].nunique()
    return {
        "n_orders": int(df["order_id"].nunique()),
        "n_customers": int(df["customer_id"].nunique()),
        "avg_items_per_order": float(n_items.mean()),
        "median_items_per_order": float(n_items.median()),
        "max_items_per_order": int(n_items.max()),
        "share_multi_item_orders": float((n_items >= 2).mean()),
        "avg_groups_per_order": float(groups.mean()),
        "basket_size_distribution": {
            int(k): int(v) for k, v in n_items.value_counts().sort_index().items()
        },
    }
