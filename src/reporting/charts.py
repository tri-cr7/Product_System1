"""Sinh biểu đồ phục vụ báo cáo và dashboard.

Toàn bộ biểu đồ dùng chung một phong cách (font DejaVu hỗ trợ tiếng Việt,
màu nhất quán theo nhóm hàng) để dễ trao đổi khi bảo vệ đồ án.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ..config import CHART_DIR  # noqa: E402

# ── Phong cách chung ─────────────────────────────────────────────────────────
PALETTE = ["#2563eb", "#f97316", "#10b981", "#a855f7", "#ef4444", "#14b8a6", "#eab308"]
GROUP_PALETTE = {
    "BOT": "#2563eb",
    "SET": "#f97316",
    "THO": "#10b981",
    "TMX": "#a855f7",
    "TTC": "#ef4444",
}

plt.rcParams.update(
    {
        "figure.dpi": 130,
        "savefig.dpi": 160,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def _save(fig, name: str, out_dir=None) -> str:
    out_dir = out_dir or CHART_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def plot_monthly_revenue(result, out_dir=None) -> str:
    """Biểu đồ mùa vụ doanh thu theo tháng."""
    df = result.monthly_stats.copy()
    df["month"] = df["order_time"].astype(str)
    fig, ax = plt.subplots(figsize=(11, 4.2))
    colors = [GROUP_PALETTE.get(g, "#64748b") for g in _month_group(df, result)]
    ax.bar(df["month"], df["revenue"], color=colors, alpha=0.9)
    ax2 = ax.twinx()
    ax2.plot(df["month"], df["n_orders"], color="#334155", marker="o", lw=1.6)
    ax2.set_ylabel("Số đơn hàng")
    ax2.grid(False)
    ax.set_ylabel("Doanh thu (VND)")
    ax.set_title("Doanh thu & số đơn hàng theo tháng – kiểm chứng mùa vụ Q4")
    ax.tick_params(axis="x", rotation=45)
    return _save(fig, "chart_01_monthly_revenue.png", out_dir)


def _month_group(df: pd.DataFrame, result) -> list[str]:
    """Gán nhóm hàng đại diện cho mỗi tháng để tô màu nhất quán."""
    if result.transactions is None:
        return []
    tx = result.transactions
    tx = tx.assign(m=tx["order_time"].dt.to_period("M").astype(str))
    top = (
        tx.groupby(["m", "group_code"])["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
        .groupby("m")
        .head(1)
        .set_index("m")["group_code"]
        .to_dict()
    )
    return [top.get(m, "SET") for m in df["month"]]


def plot_elbow_silhouette(result, out_dir=None) -> str:
    """Elbow Method + Silhouette Score – Slide 5.3."""
    elbow = result.clustering.elbow.to_frame()
    fig, ax1 = plt.subplots(figsize=(8.4, 4.4))
    ax1.plot(elbow["k"], elbow["wcss"], "o-", color="#2563eb", lw=2, label="WCSS (Inertia)")
    ax1.set_xlabel("Số cụm K")
    ax1.set_ylabel("WCSS", color="#2563eb")
    ax1.tick_params(axis="y", labelcolor="#2563eb")
    best_elbow = result.clustering.elbow.best_k_elbow
    ax1.axvline(best_elbow, ls="--", c="#f97316", label=f"Elbow → K={best_elbow}")

    ax2 = ax1.twinx()
    ax2.plot(elbow["k"], elbow["silhouette"], "s--", color="#10b981", lw=2, label="Silhouette")
    best_sil = result.clustering.elbow.best_k_silhouette
    ax2.axvline(best_sil, ls=":", c="#10b981", alpha=0.7, label=f"Silhouette max → K={best_sil}")
    ax2.set_ylabel("Silhouette Score", color="#10b981")
    ax2.tick_params(axis="y", labelcolor="#10b981")
    ax2.grid(False)

    lines = ax1.get_lines() + ax2.get_lines()
    labels = [ln.get_label() for ln in lines]
    ax1.legend(lines, labels, loc="upper right", fontsize=8, frameon=False)
    ax1.set_title(f"Đánh giá K-Means: Elbow & Silhouette (K chọn = {result.clustering.selected_k})")
    return _save(fig, "chart_02_elbow_silhouette.png", out_dir)


def plot_confusion_matrix(result, out_dir=None) -> str:
    """Confusion Matrix giữa cụm K-Means và nhãn Mã PKKH – Slide 5."""
    cmp = result.clustering.comparison
    if not cmp:
        return ""
    cm = cmp["confusion_matrix"]
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    im = ax.imshow(cm.values, cmap="Blues")
    ax.set_xticks(range(cm.shape[1]), cm.columns, rotation=30)
    ax.set_yticks(range(cm.shape[0]), cm.index)
    ax.set_xlabel("Cụm K-Means (hành vi)")
    ax.set_ylabel("Mã PKKH (nhân khẩu học)")
    ax.set_title("Confusion Matrix: hành vi vs. nhân khẩu học")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, f"{cm.values[i, j]:,}", ha="center", va="center", fontsize=8,
                    color="white" if cm.values[i, j] > cm.values.max() * 0.5 else "#0f172a")
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.grid(False)
    return _save(fig, "chart_03_confusion_matrix.png", out_dir)


def plot_lift_distribution(result, out_dir=None) -> str:
    """Phân phối Lift của các luật kết hợp."""
    rules = result.rules.rules
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.hist(rules["lift"], bins=40, color="#2563eb", alpha=0.85, edgecolor="white")
    ax.axvline(1.0, color="#ef4444", ls="--", lw=2, label="Lift = 1 (không tương quan)")
    ax.axvline(rules["lift"].mean(), color="#f97316", ls=":", lw=2,
               label=f"Lift TB = {rules['lift'].mean():.4f}")
    ax.set_xlabel("Lift")
    ax.set_ylabel("Số luật")
    ax.set_title("Phân phối Lift – đa số luật có Lift < 1 (hành vi thay thế, không bổ trợ)")
    ax.legend(frameon=False)
    return _save(fig, "chart_04_lift_distribution.png", out_dir)


def plot_chi_square_heatmap(result, out_dir=None) -> str:
    """Heatmap kiểm định chi-square PKKH × Nhóm hàng."""
    cs = result.chi_square_segment_group
    if cs is None:
        return ""
    table = cs.contingency
    fig, ax = plt.subplots(figsize=(9, 4.6))
    im = ax.imshow(table.values, cmap="Purples", aspect="auto")
    ax.set_xticks(range(table.shape[1]), table.columns, rotation=20, ha="right")
    ax.set_yticks(range(table.shape[0]), table.index)
    ax.set_title(
        f"Chi-square: Mã PKKH × Nhóm hàng (χ²={cs.chi2:.1f}, p={cs.p_value:.1e}, V={cs.cramers_v:.4f})"
    )
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            ax.text(j, i, f"{table.values[i, j]:,}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.grid(False)
    return _save(fig, "chart_05_chi_square_heatmap.png", out_dir)


def plot_strategy_comparison(result, out_dir=None) -> str:
    """So sánh 7 chiến lược gợi ý trên hold-out theo thời gian."""
    ev = result.evaluation_warm
    if ev is None or ev.empty:
        return ""
    metrics = ["precision_at_k", "recall_at_k", "hit_rate_at_k", "ndcg_at_k"]
    labels = ["Precision@5", "Recall@5", "Hit-Rate@5", "NDCG@5"]
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(ev))
    w = 0.2
    for i, (m, lb) in enumerate(zip(metrics, labels)):
        ax.bar(x + (i - 1.5) * w, ev[m], w, label=lb, color=PALETTE[i])
    ax.set_xticks(x, ev["strategy"], rotation=20, ha="right")
    ax.set_ylabel("Giá trị chỉ số")
    ax.set_title("So sánh các chiến lược gợi ý (khách warm, hold-out theo thời gian)")
    ax.legend(frameon=False, ncol=4, fontsize=9)
    return _save(fig, "chart_06_strategy_comparison.png", out_dir)


def plot_basket_size(result, out_dir=None) -> str:
    """Cấu trúc giỏ hàng & phân phối support."""
    tx = result.transactions
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    sizes = tx.groupby("order_id")["item_code"].nunique().value_counts().sort_index()
    ax1.bar(sizes.index, sizes.values, color="#2563eb", alpha=0.9)
    ax1.set_xlabel("Số mặt hàng trong đơn")
    ax1.set_ylabel("Số đơn")
    ax1.set_title("Phân phối kích thước giỏ hàng")

    sup = result.item_support.head(15).sort_values("support")
    ax2.barh(sup["item_code"], sup["support"], color="#f97316")
    ax2.set_xlabel("Support")
    ax2.set_title("Top-15 mặt hàng theo Support")
    return _save(fig, "chart_07_basket_structure.png", out_dir)


def plot_cosine_similarity(result, out_dir=None) -> str:
    """Ma trận Cosine similarity giữa các mặt hàng."""
    idx = result.item_index
    if idx is None:
        return ""
    sim = idx.similarity
    fig, ax = plt.subplots(figsize=(8.4, 7.0))
    im = ax.imshow(sim, cmap="YlGnBu", vmin=-1, vmax=1)
    ax.set_xticks(range(len(idx.codes)), idx.codes, rotation=90, fontsize=7)
    ax.set_yticks(range(len(idx.codes)), idx.codes, fontsize=7)
    ax.set_title("Ma trận Cosine similarity (TF-IDF) giữa các mặt hàng")
    fig.colorbar(im, ax=ax, shrink=0.75)
    ax.grid(False)
    return _save(fig, "chart_08_cosine_similarity.png", out_dir)


def plot_rfm_clusters(result, out_dir=None) -> str:
    """Phân cụm RFM trong không gian 3D."""
    rfm = result.rfm.frame.copy()
    rfm["cluster"] = rfm["customer_id"].map(result.clustering.labels)
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    fig = plt.figure(figsize=(9, 6.4))
    ax = fig.add_subplot(111, projection="3d")
    for i, (cl, g) in enumerate(rfm.groupby("cluster")):
        ax.scatter(
            g["log_recency"], g["log_frequency"], g["log_monetary"],
            s=6, alpha=0.55, label=f"{cl} (n={len(g):,})", color=PALETTE[i % len(PALETTE)],
        )
    ax.set_xlabel("log(Recency)")
    ax.set_ylabel("log(Frequency)")
    ax.set_zlabel("log(Monetary)")
    ax.set_title("Phân cụm K-Means trong không gian RFM")
    ax.legend(fontsize=8, frameon=False)
    return _save(fig, "chart_09_rfm_clusters_3d.png", out_dir)


def plot_cluster_profile(result, out_dir=None) -> str:
    """Hồ sơ các cụm: quy mô và giá trị trung bình."""
    prof = result.cluster_profile
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, col, title in zip(
        axes,
        ["avg_recency_days", "avg_frequency", "avg_monetary"],
        ["Recency (ngày)", "Frequency (đơn)", "Monetary (VND)"],
    ):
        ax.bar(prof["cluster"], prof[col], color=PALETTE[: len(prof)])
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=0)
    fig.suptitle("Hồ sơ đặc trưng các cụm K-Means", fontweight="bold")
    return _save(fig, "chart_10_cluster_profile.png", out_dir)


def generate_all_charts(result, out_dir=None) -> list[str]:
    """Sinh toàn bộ biểu đồ, bỏ qua biểu đồ lỗi."""
    out_dir = out_dir or CHART_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    charts = [
        plot_monthly_revenue,
        plot_elbow_silhouette,
        plot_confusion_matrix,
        plot_lift_distribution,
        plot_chi_square_heatmap,
        plot_strategy_comparison,
        plot_basket_size,
        plot_cosine_similarity,
        plot_rfm_clusters,
        plot_cluster_profile,
    ]
    paths: list[str] = []
    for fn in charts:
        try:
            p = fn(result, out_dir)
            if p:
                paths.append(p)
        except Exception as exc:  # pragma: no cover - phụ thuộc dữ liệu
            print(f"  ⚠️  Bỏ qua biểu đồ {fn.__name__}: {exc}")
    return paths
