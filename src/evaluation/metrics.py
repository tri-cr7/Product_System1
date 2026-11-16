"""Đánh giá mô hình Tầng 4 – mở rộng các chỉ số của Slide 5 sang ngữ cảnh Top-K.

* **Precision@k**: trong k gợi ý đầu, bao nhiêu là đúng?
* **Recall@k**: trong tất cả sản phẩm khách thực sự mua, bao nhiêu nằm trong k gợi ý?
* **Hit-Rate@k**: có ít nhất 1 gợi ý đúng không?
* **NDCG@k**: có trọng số vị trí (gợi ý đúng ở đầu được tính điểm cao hơn).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class EvaluationResult:
    """Kết quả đánh giá một chiến lược gợi ý."""

    strategy: str
    k: int
    n_customers: int
    precision_at_k: float
    recall_at_k: float
    hit_rate_at_k: float
    ndcg_at_k: float
    coverage: float
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "k": self.k,
            "n_customers": self.n_customers,
            "precision_at_k": self.precision_at_k,
            "recall_at_k": self.recall_at_k,
            "hit_rate_at_k": self.hit_rate_at_k,
            "ndcg_at_k": self.ndcg_at_k,
            "coverage": self.coverage,
            "notes": self.notes,
        }


def evaluate_recommendations(
    recommendations: dict[str, list[str]],
    relevant: dict[str, set[str]],
    k: int = 5,
    strategy: str = "",
    all_items: set[str] | None = None,
) -> EvaluationResult:
    """Đánh giá một bộ gợi ý theo 4 chỉ số Top-K."""
    p_sum = r_sum = h_sum = ndcg_sum = 0.0
    n = 0
    recommended_items: set[str] = set()

    for cust, rel in relevant.items():
        if not rel:
            continue
        rec = recommendations.get(cust, [])[:k]
        if not rec:
            continue
        recommended_items.update(rec)
        hits = [1.0 if item in rel else 0.0 for item in rec]
        hit_count = sum(hits)

        p_sum += hit_count / len(rec)
        r_sum += hit_count / len(rel)
        h_sum += 1.0 if hit_count > 0 else 0.0

        dcg = sum(h / np.log2(i + 2) for i, h in enumerate(hits))
        idcg = sum(1 / np.log2(i + 2) for i in range(min(len(rel), k)))
        ndcg_sum += dcg / idcg if idcg > 0 else 0.0
        n += 1

    coverage = (
        len(recommended_items) / len(all_items) if all_items else float("nan")
    )
    return EvaluationResult(
        strategy=strategy,
        k=k,
        n_customers=n,
        precision_at_k=p_sum / n if n else 0.0,
        recall_at_k=r_sum / n if n else 0.0,
        hit_rate_at_k=h_sum / n if n else 0.0,
        ndcg_at_k=ndcg_sum / n if n else 0.0,
        coverage=coverage,
    )


def build_relevance(
    test: pd.DataFrame,
    train_history: dict[str, set[str]],
) -> dict[str, set[str]]:
    """Ground truth: sản phẩm khách mua trong kỳ test, trừ sản phẩm đã mua trong train."""
    relevant: dict[str, set[str]] = {}
    for cust, items in test.groupby("customer_id")["item_code"]:
        rel = set(items.astype(str)) - train_history.get(cust, set())
        if rel:
            relevant[cust] = rel
    return relevant


def build_history(df: pd.DataFrame) -> dict[str, set[str]]:
    """Lịch sử mua: ``{customer_id: {item_code, ...}}``."""
    return (
        df.groupby("customer_id")["item_code"].apply(lambda s: set(s.astype(str))).to_dict()
    )


def split_by_time(df: pd.DataFrame, split_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Slide 5 – Hold-out **theo thời gian**.

    Vì dữ liệu có mùa vụ mạnh, chia ngẫu nhiên sẽ gây rò rỉ dữ liệu doanh thu.
    """
    cutoff = pd.Timestamp(split_date)
    train = df[df["order_time"] < cutoff].copy()
    test = df[df["order_time"] >= cutoff].copy()
    return train.reset_index(drop=True), test.reset_index(drop=True)


def evaluate_all_strategies(
    strategies: dict[str, dict[str, list[str]]],
    relevant: dict[str, set[str]],
    k: int = 5,
    all_items: set[str] | None = None,
) -> pd.DataFrame:
    """Đánh giá nhiều chiến lược cùng lúc, trả về bảng so sánh."""
    rows = []
    for name, recs in strategies.items():
        res = evaluate_recommendations(recs, relevant, k=k, strategy=name, all_items=all_items)
        rows.append(res.to_dict())
    return pd.DataFrame(rows).sort_values("precision_at_k", ascending=False).reset_index(drop=True)


def confusion_metrics(y_true: pd.Series, y_pred: pd.Series) -> dict:
    """Slide 5 – Accuracy / Precision / Recall / F1 (macro & weighted)."""
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
    )

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_precision": float(
            precision_score(y_true, y_pred, average="weighted", zero_division=0)
        ),
        "weighted_recall": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }
