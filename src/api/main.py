"""FastAPI – REST API cho hệ thống phân tích giỏ hàng & gợi ý đa tầng.

Chạy::

    uvicorn src.api.main:app --reload --port 8000

API là lớp **Operationalize** trong vòng đời Data Analytics (Slide 1): biến kết quả
phân tích thành dịch vụ mà ứng dụng khác (web/mobile) có thể gọi.
"""
from __future__ import annotations

import json
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import ARTIFACT_DIR

app = FastAPI(
    title="Hệ thống Phân tích Giỏ Hàng & Gợi ý Sản Phẩm Đa Tầng",
    description=(
        "API 4 tầng: Tiền xử lý & Thống kê → Phân cụm RFM/K-Means → "
        "Khai phá luật kết hợp → Gợi ý đa tầng (A/B/C)."
    ),
    version="1.0.0",
)


# ── Schemas ──────────────────────────────────────────────────────────────────
class RecommendationItem(BaseModel):
    item_code: str
    item_name: str
    score: float
    branch: str
    reason: str


class CustomerRecommendation(BaseModel):
    customer_id: str
    customer_type: Literal["warm", "cold"]
    segment_code: str
    branch_used: str
    recommendations: list[RecommendationItem]


class ItemInfo(BaseModel):
    item_code: str
    item_name: str
    group_name: str
    support: float | None = None
    revenue: int | None = None


class SimilarItem(BaseModel):
    item_code: str
    item_name: str
    cosine_similarity: float


class ClusterInfo(BaseModel):
    cluster: str
    n_customers: int
    share: float
    avg_recency_days: float
    avg_frequency: float
    avg_monetary: float
    total_revenue: float
    top_segment: str | None = None


class RuleInfo(BaseModel):
    antecedent: str
    consequent: str
    support: float
    confidence: float
    lift: float
    leverage: float
    conviction: float


# ── Nạp artifact ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _load_artifacts() -> dict:
    """Nạp kết quả pipeline đã lưu (tránh chạy lại pipeline mỗi request)."""
    art = Path(ARTIFACT_DIR)
    out: dict = {}

    summary_p = art / "summary.json"
    if summary_p.exists():
        out["summary"] = json.loads(summary_p.read_text(encoding="utf-8"))

    tx_p = art / "transactions.parquet"
    if tx_p.exists():
        out["transactions"] = pd.read_parquet(tx_p)

    rfm_p = art / "rfm.parquet"
    if rfm_p.exists():
        out["rfm"] = pd.read_parquet(rfm_p)

    prof_p = art / "cluster_profile.csv"
    if prof_p.exists():
        out["cluster_profile"] = pd.read_csv(prof_p)

    rules_p = art / "association_rules.csv"
    if rules_p.exists():
        out["rules"] = pd.read_csv(rules_p)

    exp_p = art / "association_rules_exploratory.csv"
    if exp_p.exists():
        out["rules_exploratory"] = pd.read_csv(exp_p)

    sup_p = art / "targeted_rules.csv"
    if sup_p.exists():
        out["targeted_rules"] = pd.read_csv(sup_p)

    sim_p = art / "item_similarity.pkl"
    if sim_p.exists():
        with open(sim_p, "rb") as fh:
            out["similarity"] = pickle.load(fh)

    ev_w = art / "eval_warm.csv"
    if ev_w.exists():
        out["eval_warm"] = pd.read_csv(ev_w)
    ev_c = art / "eval_cold.csv"
    if ev_c.exists():
        out["eval_cold"] = pd.read_csv(ev_c)

    return out


@lru_cache(maxsize=1)
def _recommender():
    """Dựng lại bộ gợi ý từ artifact (dùng chung với dashboard)."""
    from ..config import RecommenderConfig
    from ..layers.layer4_recommender import MultiLayerRecommender, build_item_index

    art = _load_artifacts()
    if "transactions" not in art:
        return None

    tx = art["transactions"]
    # Chia train/test lại đúng như lúc train để đảm bảo tính tái lập
    cutoff = pd.Timestamp("2022-10-01")
    train = tx[tx["order_time"] < cutoff].copy()
    idx = build_item_index(tx, RecommenderConfig())
    segs = tx.groupby("customer_id")["segment_code"].first().to_dict()
    return MultiLayerRecommender(
        train, idx, RecommenderConfig(), segs, all_customers=sorted(tx["customer_id"].unique())
    )


def _require(key: str):
    art = _load_artifacts()
    if key not in art:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Chưa có artifact '{key}'. Hãy chạy: "
                "`python scripts/run_pipeline.py` để sinh dữ liệu."
            ),
        )
    return art[key]


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/", tags=["meta"])
def root() -> dict:
    """Thông tin API và hướng dẫn nhanh."""
    return {
        "service": "Hệ thống Phân tích Giỏ Hàng & Gợi ý Sản Phẩm Đa Tầng",
        "version": app.version,
        "docs": "/docs",
        "endpoints": {
            "GET /summary": "Tóm tắt KPI toàn hệ thống",
            "GET /customers": "Danh sách khách hàng (lọc theo phân khúc/loại)",
            "GET /customers/{id}/recommendations": "Gợi ý đa tầng cho một khách",
            "GET /items": "Danh mục mặt hàng kèm support",
            "GET /items/{code}/similar": "Sản phẩm tương đồng (TF-IDF + Cosine)",
            "GET /clusters": "Hồ sơ các cụm K-Means",
            "GET /rules": "Luật kết hợp",
            "GET /evaluation": "Kết quả đánh giá Top-K",
        },
    }


@app.get("/summary", tags=["meta"])
def get_summary() -> dict:
    """Tóm tắt KPI toàn hệ thống sau khi chạy pipeline."""
    return _require("summary")


@app.get("/customers", tags=["customers"])
def list_customers(
    segment: str | None = Query(None, description="Lọc theo Mã PKKH (vd: A1)"),
    customer_type: Literal["warm", "cold", "all"] = Query("all"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict:
    """Danh sách khách hàng kèm phân khúc và loại khách."""
    tx = _require("transactions")
    rfm = _load_artifacts().get("rfm")
    art = _load_artifacts()

    df = tx[["customer_id", "segment_code", "segment_desc"]].drop_duplicates("customer_id")
    cutoff = pd.Timestamp("2022-10-01")
    warm_ids = set(tx[tx["order_time"] < cutoff]["customer_id"].unique())
    df["customer_type"] = np.where(df["customer_id"].isin(warm_ids), "warm", "cold")

    if segment:
        df = df[df["segment_code"] == segment]
    if customer_type != "all":
        df = df[df["customer_type"] == customer_type]

    total = len(df)
    page = df.iloc[offset : offset + limit]
    if rfm is not None:
        cols = ["customer_id", "recency", "frequency", "monetary"]
        merged = page.merge(rfm[[c for c in cols if c in rfm.columns]], on="customer_id", how="left")
    else:
        merged = page

    return {
        "total": int(total),
        "offset": offset,
        "limit": limit,
        "items": json.loads(merged.to_json(orient="records")),
    }


@app.get("/customers/{customer_id}/recommendations", tags=["customers"])
def get_recommendations(customer_id: str, k: int = Query(5, ge=1, le=20)) -> dict:
    """Gợi ý đa tầng cho một khách hàng (nhánh A/B/C kèm lý do)."""
    rec = _recommender()
    if rec is None:
        raise HTTPException(status_code=503, detail="Chưa nạp được dữ liệu. Chạy pipeline trước.")
    if customer_id not in rec.segments:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy khách hàng '{customer_id}'")

    res = rec.recommend(customer_id)
    out = res.to_dict()
    out["recommendations"] = out["recommendations"][:k]
    return out


@app.get("/items", tags=["items"])
def list_items(limit: int = Query(50, ge=1, le=500)) -> dict:
    """Danh mục mặt hàng kèm support và doanh thu."""
    art = _load_artifacts()
    tx = art.get("transactions")
    if tx is None:
        raise HTTPException(status_code=503, detail="Chưa có artifact transactions.")
    sup_p = Path(ARTIFACT_DIR) / "item_support.csv"
    if sup_p.exists():
        df = pd.read_csv(sup_p)
    else:
        n = tx["order_id"].nunique()
        df = (
            tx.groupby(["item_code", "item_name", "group_name"])
            .agg(n_orders=("order_id", "nunique"), revenue=("amount", "sum"))
            .reset_index()
        )
        df["support"] = df["n_orders"] / n
    df = df.sort_values("support", ascending=False)
    return {"total": len(df), "items": json.loads(df.head(limit).to_json(orient="records"))}


@app.get("/items/{item_code}/similar", tags=["items"])
def similar_items(item_code: str, limit: int = Query(5, ge=1, le=19)) -> dict:
    """Sản phẩm tương đồng theo TF-IDF + Cosine similarity."""
    art = _load_artifacts()
    if "similarity" not in art:
        raise HTTPException(status_code=503, detail="Chưa có ma trận similarity.")
    sim = art["similarity"]
    codes = sim["codes"]
    if item_code not in codes:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy mặt hàng '{item_code}'")

    i = codes.index(item_code)
    names = dict(zip(sim["items"]["item_code"], sim["items"]["item_name"]))
    row = sim["similarity"][i]
    order = np.argsort(-row)[: limit + 1]
    items = [
        SimilarItem(
            item_code=codes[j],
            item_name=names.get(codes[j], codes[j]),
            cosine_similarity=float(row[j]),
        )
        for j in order
        if codes[j] != item_code
    ][:limit]
    return {"item_code": item_code, "item_name": names.get(item_code, item_code), "similar": items}


@app.get("/clusters", tags=["clustering"])
def list_clusters() -> dict:
    """Hồ sơ các cụm K-Means (RFM)."""
    df = _require("cluster_profile")
    return {"total": len(df), "clusters": json.loads(df.to_json(orient="records"))}


@app.get("/rules", tags=["mba"])
def list_rules(
    min_lift: float = Query(0.0),
    min_support: float = Query(0.0),
    limit: int = Query(50, ge=1, le=500),
    scope: Literal["operational", "exploratory", "both"] = Query(
        "both", description="'operational' = lọc support ≥ 1%, 'exploratory' = toàn bộ cặp"
    ),
) -> dict:
    """Luật kết hợp, lọc theo lift / support.

    * ``operational`` – bộ luật dùng được (support ≥ 1%).
    * ``exploratory`` – toàn bộ cặp có support > 0, để thấy đầy đủ phân phối Lift.
    """
    art = _load_artifacts()
    frames = []
    if scope in {"operational", "both"} and "rules" in art:
        frames.append(art["rules"])
    if scope in {"exploratory", "both"} and "rules_exploratory" in art:
        frames.append(art["rules_exploratory"])
    if not frames:
        raise HTTPException(status_code=503, detail="Chưa có dữ liệu luật kết hợp.")

    df = pd.concat(frames, ignore_index=True).drop_duplicates(
        subset=["antecedent", "consequent"]
    )
    df = df[(df["lift"] >= min_lift) & (df["support"] >= min_support)]
    df = df.sort_values(["lift", "support"], ascending=[False, False]).head(limit)
    return {"total": len(df), "scope": scope, "rules": json.loads(df.to_json(orient="records"))}


@app.get("/evaluation", tags=["evaluation"])
def get_evaluation() -> dict:
    """Kết quả đánh giá Top-K trên hold-out theo thời gian."""
    art = _load_artifacts()
    out = {}
    for key, label in (("eval_warm", "warm"), ("eval_cold", "cold")):
        if key in art:
            out[label] = json.loads(art[key].to_json(orient="records"))
    if not out:
        raise HTTPException(status_code=503, detail="Chưa có kết quả đánh giá.")
    return out


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Kiểm tra trạng thái dịch vụ và artifact."""
    art = _load_artifacts()
    return {
        "status": "ok" if art else "no-artifacts",
        "available_artifacts": sorted(art.keys()),
    }
