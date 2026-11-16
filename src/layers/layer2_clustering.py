"""Tầng 2 – Đặc trưng RFM (mở rộng) và phân cụm K-Means (Slide 5.3).

Slide 5.3 trang 20 đặt câu hỏi mở *"Làm thế nào để đánh giá hiệu quả của K-means?"* –
module này trả lời bằng **Elbow Method** và **Silhouette Score**.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score

from ..config import ClusterConfig, RFMConfig
from .layer1_preprocessing import log_transform, min_max_scale, zscore_scale


@dataclass
class RFMResult:
    """Bảng đặc trưng RFM của từng khách hàng."""

    frame: pd.DataFrame
    reference_date: pd.Timestamp
    feature_columns: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def n_customers(self) -> int:
        return len(self.frame)


def compute_rfm(df: pd.DataFrame, config: RFMConfig | None = None) -> RFMResult:
    """Tạo đặc trưng RFM cho từng khách hàng.

    * **R** (Recency): số ngày kể từ đơn hàng cuối cùng — càng nhỏ càng tích cực.
    * **F** (Frequency): số đơn hàng trong kỳ.
    * **M** (Monetary): tổng chi tiêu.

    Vì F và M có phân phối lệch phải mạnh, áp dụng **log transform** trước khi
    chuẩn hóa để trục M không chiếm trọn không gian đặc trưng.
    """
    config = config or RFMConfig()
    notes: list[str] = []

    ref = (
        pd.Timestamp(config.reference_date)
        if config.reference_date
        else df["order_time"].max()
    )
    notes.append(f"Mốc thời gian tham chiếu: {ref:%Y-%m-%d %H:%M}")

    agg = df.groupby("customer_id").agg(
        last_order=("order_time", "max"),
        first_order=("order_time", "min"),
        n_orders=("order_id", "nunique"),
        n_items=("item_code", "nunique"),
        revenue=("amount", "sum"),
        n_days=("order_time", lambda s: (s.max() - s.min()).days),
    )
    agg["recency"] = (ref - agg["last_order"]).dt.days
    agg["frequency"] = agg["n_orders"]
    agg["monetary"] = agg["revenue"]

    feats = pd.DataFrame(index=agg.index)
    for col in ("recency", "frequency", "monetary"):
        s = agg[col].astype(float)
        if config.log_transform:
            feats[f"log_{col}"] = log_transform(s)
        else:
            feats[col] = s

    if config.scaler == "minmax":
        for col in feats.columns:
            feats[col] = min_max_scale(feats[col])
        notes.append("Chuẩn hóa Min-Max Scaling (Slide 1.1)")
    else:
        for col in feats.columns:
            feats[col] = zscore_scale(feats[col])
        notes.append("Chuẩn hóa Z-score Normalization (Slide 1.1)")

    out = agg.join(feats)
    out["customer_segment"] = df.groupby("customer_id")["segment_code"].first()
    out["segment_desc"] = df.groupby("customer_id")["segment_desc"].first()

    return RFMResult(
        frame=out.reset_index(),
        reference_date=ref,
        feature_columns=list(feats.columns),
        notes=notes,
    )


def rfm_segment_labels(rfm: pd.DataFrame) -> pd.Series:
    """Gán nhãn kinh doanh theo quy tắc R–F–M (thang điểm 1–5)."""
    r, f, m = rfm["recency"], rfm["frequency"], rfm["monetary"]

    def _score(s: pd.Series, ascending: bool) -> pd.Series:
        pct = s.rank(pct=True, ascending=ascending)
        return pd.cut(pct, bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=[1, 2, 3, 4, 5]).astype(int)

    r_score, f_score, m_score = _score(r, False), _score(f, True), _score(m, True)

    def _label(rs: int, fs: int, ms: int) -> str:
        total = rs + fs + ms
        if rs >= 4 and fs >= 4 and ms >= 4:
            return "VIP"
        if rs >= 4 and fs <= 2:
            return "Cần chăm sóc (At-risk)"
        if rs >= 3 and fs >= 3:
            return "Trung thành"
        if total <= 6:
            return "Mới / ít tương tác"
        return "Trung bình"

    return pd.Series(
        [_label(a, b, c) for a, b, c in zip(r_score, f_score, m_score)],
        index=rfm.index,
        name="rfm_label",
    )


@dataclass
class ElbowCurve:
    """Đường cong WCSS + Silhouette theo số cụm K."""

    k_values: list[int]
    wcss: list[float]
    silhouette: list[float]

    @property
    def best_k_silhouette(self) -> int:
        return int(self.k_values[int(np.argmax(self.silhouette))])

    @property
    def best_k_elbow(self) -> int:
        """Điểm gấp (knee) theo phương pháp khoảng cách tới đường thẳng nối hai đầu."""
        w = np.asarray(self.wcss, dtype=float)
        k = np.asarray(self.k_values, dtype=float)
        wn = (w - w.min()) / (w.max() - w.min() or 1.0)
        kn = (k - k.min()) / (k.max() - k.min() or 1.0)
        x0, y0, x1, y1 = kn[0], wn[0], kn[-1], wn[-1]
        dist = np.abs((y1 - y0) * kn - (x1 - x0) * wn + x1 * y0 - y1 * x0)
        dist /= np.hypot(y1 - y0, x1 - x0)
        return int(self.k_values[int(np.argmax(dist))])

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"k": self.k_values, "wcss": self.wcss, "silhouette": self.silhouette}
        )


@dataclass
class ClusteringResult:
    """Kết quả phân cụm K-Means cùng đánh giá đối chiếu với nhãn PKKH."""

    labels: pd.Series
    features: pd.DataFrame
    elbow: ElbowCurve
    selected_k: int
    inertia: float
    silhouette: float
    sizes: dict[str, int]
    comparison: dict | None = None
    notes: list[str] = field(default_factory=list)


def _optimal_mapping(y_true: pd.Series, y_pred: pd.Series):
    """Gán nhãn tối ưu 1-1 giữa cụm K-Means và nhãn thật (Hungarian algorithm).

    Ma trận có thể không vuông (9 nhãn PKKH × 3 cụm) – thuật toán chỉ ghép được
    ``min(r, c)`` cặp.
    """
    labs_true = sorted(y_true.unique())
    labs_pred = sorted(y_pred.unique())
    cm = (
        pd.crosstab(y_true, y_pred)
        .reindex(index=labs_true, columns=labs_pred, fill_value=0)
        .values
    )
    row, col = linear_sum_assignment(-cm)
    acc = cm[row, col].sum() / max(len(y_true), 1)
    return cm, row, col, acc


def evaluate_against_segments(
    y_true: pd.Series, y_pred: pd.Series, n_classes_true: int
) -> dict:
    """Slide 5 – Confusion Matrix + Accuracy / Precision / Recall / F1.

    So sánh cụm hành vi (K-Means trên RFM) với phân khúc nhân khẩu học (``Mã PKKH``)
    để **kiểm chứng** chất lớp phân cụm.

    Vì số nhãn thật (9) khác số cụm (3), các chỉ số được tính theo hai góc:

    * **Precision theo cụm** – trong cụm *c*, tỷ lệ khách thuộc nhãn PKKH phổ biến nhất.
    * **Recall theo nhãn** – với nhãn PKKH *t*, tỷ lệ khách của *t* nằm vào cụm đông nhất.
    """
    d = pd.DataFrame({"true": y_true, "pred": y_pred}).dropna()
    labs_true = sorted(d["true"].unique())
    labs_pred = sorted(d["pred"].unique())
    cm = (
        pd.crosstab(d["true"], d["pred"])
        .reindex(index=labs_true, columns=labs_pred, fill_value=0)
        .values
    )
    _cm_raw, row, col, acc_optimal = _optimal_mapping(d["true"], d["pred"])

    n_total = int(cm.sum())

    # ── Precision theo cụm (mỗi cột của confusion matrix) ──────────────────
    col_totals = cm.sum(axis=0).astype(float)
    col_max = cm.max(axis=0).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        prec_cluster = np.where(col_totals > 0, col_max / col_totals, 0.0)

    # ── Recall theo nhãn PKKH (mỗi hàng) ───────────────────────────────────
    row_totals = cm.sum(axis=1).astype(float)
    row_max = cm.max(axis=1).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        rec_label = np.where(row_totals > 0, row_max / row_totals, 0.0)

    # ── F1 tương ứng (mức cụm) ───────────────────────────────────────────
    f1_cluster = np.where(
        (prec_cluster + rec_label.mean()) > 0,
        2 * prec_cluster * rec_label.mean()
        / np.where((prec_cluster + rec_label.mean()) > 0, prec_cluster + rec_label.mean(), 1.0),
        0.0,
    )

    purity = float(col_max.sum() / n_total) if n_total else 0.0
    random_baseline = 1.0 / max(n_classes_true, 1)

    return {
        "n_samples": int(len(d)),
        "accuracy_optimal": float(acc_optimal),
        "purity": purity,
        "random_baseline": float(random_baseline),
        "macro_precision": float(prec_cluster.mean()),
        "macro_recall": float(rec_label.mean()),
        "macro_f1": float(f1_cluster.mean()),
        "weighted_precision": float(
            np.average(prec_cluster, weights=col_totals) if col_totals.sum() else 0.0
        ),
        "weighted_recall": float(
            np.average(rec_label, weights=row_totals) if row_totals.sum() else 0.0
        ),
        "weighted_f1": float(
            np.average(f1_cluster, weights=col_totals) if col_totals.sum() else 0.0
        ),
        "adjusted_rand_index": float(adjusted_rand_score(d["true"], d["pred"])),
        "confusion_matrix": pd.DataFrame(cm, index=labs_true, columns=labs_pred),
        "exceeds_random": bool(purity > random_baseline),
    }


def run_kmeans(
    rfm: RFMResult,
    config: ClusterConfig | None = None,
    segment_column: str = "customer_segment",
) -> ClusteringResult:
    """Chạy Lloyd K-Means (Slide 5.3) và đánh giá bằng Elbow + Silhouette.

    Thuật toán Lloyd gồm 3 bước lặp:
    1. *Assignment* – gán mỗi điểm vào centroid gần nhất.
    2. *Update* – tính lại centroid của mỗi cụm.
    3. *Convergence check* – dừng khi centroid không đổi.
    """
    config = config or ClusterConfig()
    X = rfm.frame[rfm.feature_columns].to_numpy(dtype=float)

    ks, wcss, sil = [], [], []
    for k in range(config.k_range[0], config.k_range[1] + 1):
        km = KMeans(n_clusters=k, n_init=config.n_init, random_state=config.random_state)
        km.fit(X)
        ks.append(k)
        wcss.append(float(km.inertia_))
        sil.append(float(silhouette_score(X, km.labels_)))
    elbow = ElbowCurve(k_values=ks, wcss=wcss, silhouette=sil)

    km = KMeans(
        n_clusters=config.selected_k,
        n_init=config.n_init,
        random_state=config.random_state,
    ).fit(X)
    labels = pd.Series(
        [f"C{i}" for i in km.labels_],
        index=rfm.frame["customer_id"],
        name="cluster",
    )

    sizes = {str(k): int(v) for k, v in labels.value_counts().sort_index().items()}
    notes = [
        f"Elbow (knee) chỉ K = {elbow.best_k_elbow}",
        f"Silhouette đạt đỉnh K = {elbow.best_k_silhouette} ({max(sil):.4f}); "
        f"chọn K = {config.selected_k} theo tiêu chí nghiệp vụ",
    ]

    comparison = None
    if segment_column in rfm.frame.columns:
        seg = rfm.frame.set_index("customer_id")[segment_column]
        comparison = evaluate_against_segments(
            seg.reindex(labels.index), labels, n_classes_true=int(seg.nunique())
        )
        notes.append(
            f"Purity = {comparison['purity']:.4f} so với ngưỡng ngẫu nhiên "
            f"{comparison['random_baseline']:.4f} → "
            + (
                "cao hơn"
                if comparison["exceeds_random"]
                else "THẤP HƠN → hai hệ phân khúc độc lập về mặt thống kê"
            )
        )

    return ClusteringResult(
        labels=labels,
        features=rfm.frame[rfm.feature_columns].copy(),
        elbow=elbow,
        selected_k=config.selected_k,
        inertia=float(km.inertia_),
        silhouette=float(silhouette_score(X, km.labels_)),
        sizes=sizes,
        comparison=comparison,
        notes=notes,
    )


def cluster_profile(
    rfm: pd.DataFrame,
    labels: pd.Series,
    segment_column: str = "customer_segment",
) -> pd.DataFrame:
    """Hồ sơ đặc trưng của từng cụm: quy mô + hành vi trội đại diện."""
    d = rfm.copy()
    d["cluster"] = d["customer_id"].map(labels)
    rows = []
    for cl, g in d.groupby("cluster"):
        row = {
            "cluster": cl,
            "n_customers": len(g),
            "share": len(g) / len(d),
            "avg_recency_days": g["recency"].mean(),
            "avg_frequency": g["frequency"].mean(),
            "avg_monetary": g["monetary"].mean(),
            "total_revenue": g["monetary"].sum(),
        }
        if segment_column in g.columns:
            vc = g[segment_column].value_counts()
            row["top_segment"] = vc.index[0]
            row["top_segment_share"] = vc.iloc[0] / len(g)
            row["segment_mix"] = ", ".join(f"{k}:{v}" for k, v in vc.head(4).items())
        rows.append(row)
    return pd.DataFrame(rows).sort_values("n_customers", ascending=False).reset_index(drop=True)
