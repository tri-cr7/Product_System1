"""Pipeline điều phối toàn bộ 4 tầng của hệ thống.

Chạy: ``python scripts/run_pipeline.py``
"""
from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ARTIFACT_DIR, CONFIG, SystemConfig
from .data.loader import load_transactions
from .data.quality import QualityCheck, run_all_checks
from .evaluation.metrics import (
    build_history,
    build_relevance,
    evaluate_all_strategies,
    split_by_time,
)
from .layers import layer1_preprocessing as l1
from .layers import layer1_statistics as l1s
from .layers import layer2_clustering as l2
from .layers import layer3_mba as l3
from .layers import layer4_recommender as l4


@dataclass
class PipelineResult:
    """Toàn bộ kết quả của một lần chạy pipeline."""

    started_at: datetime
    finished_at: datetime | None = None
    config: SystemConfig = field(default_factory=SystemConfig)

    transactions: pd.DataFrame | None = None
    quality_checks: list[QualityCheck] = field(default_factory=list)
    load_log: list[str] = field(default_factory=list)
    prep_log: list[str] = field(default_factory=list)

    outlier_reports: list = field(default_factory=list)
    chi_square_segment_group: object | None = None
    descriptive_stats: pd.DataFrame | None = None
    monthly_stats: pd.DataFrame | None = None
    basket_stats: dict = field(default_factory=dict)
    correlation: dict = field(default_factory=dict)

    rfm: object | None = None
    clustering: object | None = None
    cluster_profile: pd.DataFrame | None = None

    rules: object | None = None
    rules_exploratory: object | None = None
    rule_tests: pd.DataFrame | None = None
    targeted_rules: pd.DataFrame | None = None
    item_support: pd.DataFrame | None = None

    item_index: object | None = None
    multi_layer: object | None = None
    strategies: dict = field(default_factory=dict)
    evaluation_warm: pd.DataFrame | None = None
    evaluation_cold: pd.DataFrame | None = None

    def summary(self) -> dict:
        """Tóm tắt JSON-friendly cho API và báo cáo."""
        out: dict = {
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "n_rows": int(len(self.transactions)) if self.transactions is not None else 0,
            "n_orders": int(self.transactions["order_id"].nunique())
            if self.transactions is not None
            else 0,
            "n_customers": int(self.transactions["customer_id"].nunique())
            if self.transactions is not None
            else 0,
            "quality_passed": sum(1 for c in self.quality_checks if c.passed),
            "quality_total": len(self.quality_checks),
            "chi_square": self.chi_square_segment_group.to_dict()
            if self.chi_square_segment_group
            else None,
        }
        if self.clustering is not None:
            comp = self.clustering.comparison or {}
            out["clustering"] = {
                "selected_k": self.clustering.selected_k,
                "silhouette": self.clustering.silhouette,
                "best_k_silhouette": self.clustering.elbow.best_k_silhouette,
                "best_k_elbow": self.clustering.elbow.best_k_elbow,
                "sizes": self.clustering.sizes,
                "comparison": {k: v for k, v in comp.items() if k != "confusion_matrix"},
            }
        if self.rules is not None:
            df = self.rules.rules
            out["mba"] = {
                "n_rules": self.rules.n_rules,
                "n_baskets": self.rules.n_baskets,
                "n_lift_gt_1": int((df["lift"] > 1).sum()) if not df.empty else 0,
                "mean_lift": float(df["lift"].mean()) if not df.empty else None,
            }
        if self.evaluation_warm is not None:
            out["evaluation_warm"] = self.evaluation_warm.to_dict("records")
        if self.evaluation_cold is not None:
            out["evaluation_cold"] = self.evaluation_cold.to_dict("records")
        return out


def _json_default(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    return str(obj)


def run_pipeline(
    config: SystemConfig | None = None,
    data_path: str | Path | None = None,
    verbose: bool = True,
) -> PipelineResult:
    """Chạy toàn bộ hệ thống 4 tầng và trả về toàn bộ kết quả."""
    config = config or CONFIG
    config.ensure_dirs()
    result = PipelineResult(started_at=datetime.now(), config=config)

    def log(msg: str) -> None:
        if verbose:
            print(msg, flush=True)

    # ── TẢI & KIỂM ĐỊNH ─────────────────────────────────────────────────────
    log("[1/9] Tải dữ liệu...")
    load = load_transactions(data_path) if data_path else load_transactions()
    df = load.frame
    result.transactions = df
    result.load_log = load.transformations
    log(
        f"      {len(df):,} dòng | {df['order_id'].nunique():,} đơn "
        f"| {df['customer_id'].nunique():,} khách"
    )

    result.quality_checks = run_all_checks(df)
    n_fail = sum(1 for c in result.quality_checks if not c.passed)
    log(
        f"      Kiểm định chất lượng: {len(result.quality_checks) - n_fail}"
        f"/{len(result.quality_checks)} đạt"
    )

    # ── TẦNG 1: TIỀN XỬ LÝ & THỐNG KÊ ──────────────────────────────────────
    log("[2/9] Tầng 1 – tiền xử lý & thống kê mô tả...")
    df, miss_log = l1.handle_missing(df, config.preprocess)
    df, n_dup = l1.drop_duplicates(df)
    df, out_reports = l1.flag_outliers(
        df,
        config.preprocess.outlier_keep_columns,
        config.preprocess.iqr_multiplier,
    )
    df, bin_log = l1.add_binning(
        df, config.preprocess.binning_columns, config.preprocess.binning_bins
    )
    result.prep_log = miss_log + bin_log + [f"drop_duplicates: loại {n_dup} dòng"]
    result.outlier_reports = out_reports
    result.transactions = df

    result.descriptive_stats = l1.describe_numeric(df)
    result.monthly_stats = (
        df.groupby(df["order_time"].dt.to_period("M"))
        .agg(revenue=("amount", "sum"), n_orders=("order_id", "nunique"))
        .reset_index()
    )
    result.basket_stats = l3.basket_statistics(df)
    result.correlation = l1.pearson_correlation(df, "quantity", "amount")

    result.chi_square_segment_group = l1s.chi_square_test(
        df,
        "segment_code",
        "group_name",
        alpha=config.preprocess.chi_square_alpha,
        name="Mã PKKH × Tên nhóm hàng",
    )
    cs = result.chi_square_segment_group
    log(
        f"      Chi-square {cs.name}: χ²={cs.chi2:.2f}, p={cs.p_value:.2e}, "
        f"V={cs.cramers_v:.4f}"
    )

    # ── TẦNG 2: PHÂN CỤM ────────────────────────────────────────────────────
    log("[3/9] Tầng 2 – RFM + K-Means...")
    result.rfm = l2.compute_rfm(df, config.rfm)
    result.clustering = l2.run_kmeans(result.rfm, config.cluster)
    result.cluster_profile = l2.cluster_profile(
        result.rfm.frame, result.clustering.labels
    )
    log(
        f"      K={result.clustering.selected_k} | "
        f"Silhouette={result.clustering.silhouette:.4f} "
        f"| Elbow={result.clustering.elbow.best_k_elbow}"
    )
    if result.clustering.comparison:
        cmp = result.clustering.comparison
        log(
            f"      Purity vs PKKH = {cmp['purity']:.4f} "
            f"(ngưỡng ngẫu nhiên {cmp['random_baseline']:.4f})"
        )

    # ── TẦNG 3: MBA ────────────────────────────────────────────────────────
    log("[4/9] Tầng 3 – khai phá luật kết hợp...")
    # Bộ luật "vận hành" (min_support = 1%) và bộ luật "khám phá" (toàn bộ cặp)
    result.rules = l3.mine_association_rules(df, config.mba)
    result.rules_exploratory = l3.mine_association_rules(
        df, config.mba, min_support=0.0, min_confidence=0.0
    )
    result.rule_tests = l3.test_rules_significance(
        df, result.rules.rules, top_n=10, alpha=config.mba.chi_square_alpha
    )
    result.targeted_rules = l3.targeted_rules_by_segment(df, config.mba)
    result.item_support = l3.item_support_table(df)
    log(
        f"      {result.rules.n_rules} luật (support ≥ {config.mba.min_support}) | "
        f"{result.rules_exploratory.n_rules} luật khám phá toàn bộ | "
        f"{int((result.rules_exploratory.rules['lift'] > 1).sum())} luật có Lift > 1"
    )

    # ── TẦNG 4: GỢI Ý ──────────────────────────────────────────────────────
    log("[5/9] Tầng 4 – dựng chỉ số nội dung (TF-IDF + Cosine)...")
    result.item_index = l4.build_item_index(df, config.recommender)

    log("[6/9] Tầng 4 – chia hold-out theo thời gian & dựng chiến lược...")
    train, test = split_by_time(df, config.evaluation.split_date)
    history = build_history(train)
    log(
        f"      Train {len(train):,} dòng (đến {config.evaluation.split_date}) | "
        f"Test {len(test):,} dòng"
    )

    all_customers = sorted(df["customer_id"].unique())
    # Mã PKKH là thuộc tính nhân khẩu học tĩnh → dùng cho cả khách lạnh
    customer_segments = (
        df.groupby("customer_id")["segment_code"].first().to_dict()
    )

    def _norm(s: l4.StrategyOutput) -> l4.StrategyOutput:
        return l4.normalize_scores(s)

    strategies: dict = {
        "random": l4.strategy_random(train, all_customers, seed=config.random_state),
        "popularity": _norm(l4.strategy_global_popularity(train, all_customers)),
        "segment": _norm(
            l4.strategy_segment_popularity(train, all_customers, customer_segments)
        ),
        "segment_lift": _norm(
            l4.strategy_segment_lift(train, all_customers, customer_segments)
        ),
        "content": _norm(
            l4.strategy_content_based(
                train,
                all_customers,
                result.item_index,
                top_n=config.recommender.top_k,
            )
        ),
        "rule": _norm(
            l4.strategy_association_rules(
                train,
                all_customers,
                min_confidence=config.recommender.min_rule_confidence,
            )
        ),
    }

    # Hệ thống 3 nhánh A/B/C (kiến trúc chính của Tầng 4)
    multi = l4.MultiLayerRecommender(
        train,
        result.item_index,
        config.recommender,
        customer_segments,
        all_customers=all_customers,
    )
    result.multi_layer = multi

    multi_recs: dict[str, list[str]] = {}
    for cust in all_customers:
        multi_recs[cust] = [r.item_code for r in multi.recommend(cust).recommendations]
    strategies["multilayer"] = l4.StrategyOutput("ĐA TẦNG (A+B+C)", multi_recs)

    # Biến thể arbitration của toàn bộ chiến lược (để so sánh công bằng)
    hybrid_recs: dict[str, list[str]] = {}
    for cust in all_customers:
        ranked = l4.arbitrate(
            cust,
            history.get(cust, set()),
            strategies,
            config.recommender.weights,
            top_k=config.recommender.top_k,
            fallback_items=list(
                strategies["popularity"].recommendations.get(cust, [])[
                    : config.recommender.top_k
                ]
            ),
        )
        hybrid_recs[cust] = [c for c, _ in ranked]
    strategies["hybrid"] = l4.StrategyOutput("Arbitration tất cả", hybrid_recs)
    result.strategies = strategies

    log("[7/9] Đánh giá trên hold-out theo thời gian...")
    warm_cust = [c for c in all_customers if c in history]
    cold_cust = [c for c in all_customers if c not in history]
    all_items = set(df["item_code"].unique())

    rel_warm = build_relevance(test[test["customer_id"].isin(warm_cust)], history)
    rel_cold = build_relevance(test[test["customer_id"].isin(cold_cust)], history)

    result.evaluation_warm = evaluate_all_strategies(
        {k: v.recommendations for k, v in strategies.items()},
        rel_warm,
        k=config.evaluation.k,
        all_items=all_items,
    )
    result.evaluation_cold = evaluate_all_strategies(
        {k: v.recommendations for k, v in strategies.items()},
        rel_cold,
        k=config.evaluation.k,
        all_items=all_items,
    )
    log(
        f"      WARM (n={len(rel_warm)}): {result.evaluation_warm.iloc[0]['strategy']} "
        f"P@{config.evaluation.k} = {result.evaluation_warm.iloc[0]['precision_at_k']:.4f}"
    )
    log(
        f"      COLD (n={len(rel_cold)}): {result.evaluation_cold.iloc[0]['strategy']} "
        f"P@{config.evaluation.k} = {result.evaluation_cold.iloc[0]['precision_at_k']:.4f}"
    )

    result.finished_at = datetime.now()
    return result


def save_artifacts(result: PipelineResult, artifact_dir: Path | None = None) -> dict:
    """Lưu kết quả để API / dashboard dùng lại mà không phải chạy lại pipeline."""
    artifact_dir = Path(artifact_dir or ARTIFACT_DIR)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    (artifact_dir / "summary.json").write_text(
        json.dumps(result.summary(), ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    paths["summary"] = artifact_dir / "summary.json"

    if result.transactions is not None:
        p = artifact_dir / "transactions.parquet"
        result.transactions.to_parquet(p, index=False)
        paths["transactions"] = p
    if result.rfm is not None:
        p = artifact_dir / "rfm.parquet"
        result.rfm.frame.to_parquet(p, index=False)
        paths["rfm"] = p
    if result.cluster_profile is not None:
        p = artifact_dir / "cluster_profile.csv"
        result.cluster_profile.to_csv(p, index=False)
        paths["cluster_profile"] = p
    if result.rules is not None and not result.rules.rules.empty:
        p = artifact_dir / "association_rules.csv"
        result.rules.rules.to_csv(p, index=False)
        paths["rules"] = p
    if result.rules_exploratory is not None and not result.rules_exploratory.rules.empty:
        p = artifact_dir / "association_rules_exploratory.csv"
        result.rules_exploratory.rules.to_csv(p, index=False)
        paths["rules_exploratory"] = p
    if result.rule_tests is not None and not result.rule_tests.empty:
        p = artifact_dir / "rule_significance.csv"
        result.rule_tests.to_csv(p, index=False)
        paths["rule_tests"] = p
    if result.targeted_rules is not None and not result.targeted_rules.empty:
        p = artifact_dir / "targeted_rules.csv"
        result.targeted_rules.to_csv(p, index=False)
        paths["targeted_rules"] = p
    if result.evaluation_warm is not None:
        p = artifact_dir / "eval_warm.csv"
        result.evaluation_warm.to_csv(p, index=False)
        paths["eval_warm"] = p
    if result.evaluation_cold is not None:
        p = artifact_dir / "eval_cold.csv"
        result.evaluation_cold.to_csv(p, index=False)
        paths["eval_cold"] = p
    if result.item_support is not None:
        p = artifact_dir / "item_support.csv"
        result.item_support.to_csv(p, index=False)
        paths["item_support"] = p
    if result.item_index is not None:
        p = artifact_dir / "item_similarity.pkl"
        with open(p, "wb") as fh:
            pickle.dump(
                {
                    "codes": result.item_index.codes,
                    "items": result.item_index.items,
                    "similarity": result.item_index.similarity,
                },
                fh,
            )
        paths["similarity"] = p
    return paths
