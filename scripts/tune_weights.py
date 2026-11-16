#!/usr/bin/env python
"""Sweep trọng số gộp tín hiệu cho Tầng 4.

Dựng toàn bộ chiến lược **một lần**, sau đó chỉ thay đổi trọng số để tìm cấu hình
tối ưu theo P@5 / NDCG@5 trên tập hold-out.

Usage::

    python scripts/tune_weights.py
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.config import RecommenderConfig  # noqa: E402
from src.data.loader import load_transactions  # noqa: E402
from src.evaluation.metrics import (  # noqa: E402
    build_history,
    build_relevance,
    evaluate_all_strategies,
    split_by_time,
)
from src.layers import layer4_recommender as l4  # noqa: E402

SPLIT_DATE = "2022-10-01"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default=SPLIT_DATE)
    args = ap.parse_args()

    df = load_transactions().frame
    train, test = split_by_time(df, args.split)
    hist = build_history(train)
    segs = df.groupby("customer_id")["segment_code"].first().to_dict()
    idx = l4.build_item_index(df, RecommenderConfig())
    allc = sorted(df["customer_id"].unique())
    warm = [c for c in allc if c in hist]
    cold = [c for c in allc if c not in hist]
    rel_w = build_relevance(test[test["customer_id"].isin(warm)], hist)
    rel_c = build_relevance(test[test["customer_id"].isin(cold)], hist)

    base_cfg = RecommenderConfig()
    multi = l4.MultiLayerRecommender(
        train, idx, base_cfg, segs, all_customers=allc
    )

    rows = []
    grid_rule = [0.5, 1.0, 1.5, 2.0]
    grid_content = [0.0, 0.2, 0.4]
    grid_lift = [0.0, 0.2]
    grid_segment = [0.0, 0.3, 0.6, 1.0]

    for wr, wc, wl, ws in itertools.product(
        grid_rule, grid_content, grid_lift, grid_segment
    ):
        multi.config = RecommenderConfig(
            top_k=base_cfg.top_k,
            weights={
                "rule": wr,
                "segment": ws,
                "segment_lift": wl,
                "content": wc,
            },
        )
        recs = {c: [r.item_code for r in multi.recommend(c).recommendations] for c in allc}
        rw = evaluate_all_strategies({"ml": recs}, rel_w, k=base_cfg.top_k).iloc[0]
        rc = evaluate_all_strategies({"ml": recs}, rel_c, k=base_cfg.top_k).iloc[0]
        rows.append(
            {
                "w_rule": wr,
                "w_content": wc,
                "w_lift": wl,
                "w_segment": ws,
                "warm_P@5": rw["precision_at_k"],
                "warm_NDCG@5": rw["ndcg_at_k"],
                "cold_P@5": rc["precision_at_k"],
                "cold_NDCG@5": rc["ndcg_at_k"],
                "avg_P@5": (rw["precision_at_k"] + rc["precision_at_k"]) / 2,
            }
        )
        print(
            f"rule={wr} content={wc} lift={wl} seg={ws} | "
            f"warm P={rw['precision_at_k']:.4f} N={rw['ndcg_at_k']:.4f} | "
            f"cold P={rc['precision_at_k']:.4f} N={rc['ndcg_at_k']:.4f}",
            flush=True,
        )

    out = pd.DataFrame(rows).sort_values("avg_P@5", ascending=False)
    print("\n=== TOP-10 cấu hình ===")
    print(out.head(10).to_string(index=False))
    out_path = ROOT / "output" / "artifacts" / "weight_sweep.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"\n→ {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
