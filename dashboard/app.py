"""Streamlit – Dashboard trình bày kết quả hệ thống.

Chạy::

    streamlit run dashboard/app.py

Dashboard đọc artifact đã sinh bởi ``scripts/run_pipeline.py``; nếu chưa có thì
nút "Chạy lại pipeline" cho phép dựng lại ngay trên giao diện.
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import ARTIFACT_DIR, CHART_DIR, CONFIG  # noqa: E402

st.set_page_config(
    page_title="Hệ thống Phân tích Giỏ Hàng & Gợi ý Đa Tầng",
    page_icon="🛒",
    layout="wide",
)


@st.cache_resource(show_spinner="Đang dựng lại bộ gợi ý…")
def load_recommender():
    from src.layers.layer4_recommender import MultiLayerRecommender, build_item_index

    tx = pd.read_parquet(ARTIFACT_DIR / "transactions.parquet")
    cutoff = pd.Timestamp(CONFIG.evaluation.split_date)
    train = tx[tx["order_time"] < cutoff].copy()
    idx = build_item_index(tx, CONFIG.recommender)
    segs = tx.groupby("customer_id")["segment_code"].first().to_dict()
    return MultiLayerRecommender(
        train,
        idx,
        CONFIG.recommender,
        segs,
        all_customers=sorted(tx["customer_id"].unique()),
    )


@st.cache_data
def load_artifacts() -> dict:
    art: dict = {}
    if (ARTIFACT_DIR / "summary.json").exists():
        art["summary"] = json.loads((ARTIFACT_DIR / "summary.json").read_text(encoding="utf-8"))
    for name, fn in [
        ("transactions", "transactions.parquet"),
        ("rfm", "rfm.parquet"),
        ("cluster_profile", "cluster_profile.csv"),
        ("rules", "association_rules.csv"),
        ("rules_exploratory", "association_rules_exploratory.csv"),
        ("item_support", "item_support.csv"),
        ("targeted_rules", "targeted_rules.csv"),
        ("eval_warm", "eval_warm.csv"),
        ("eval_cold", "eval_cold.csv"),
        ("rule_tests", "rule_significance.csv"),
    ]:
        p = ARTIFACT_DIR / fn
        if p.exists():
            art[name] = pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)
    p = ARTIFACT_DIR / "item_similarity.pkl"
    if p.exists():
        with open(p, "rb") as fh:
            art["similarity"] = pickle.load(fh)
    return art


def fmt_vnd(x: float) -> str:
    return f"{x:,.0f} đ".replace(",", ".")


# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Điều khiển")
if st.sidebar.button("🔄 Chạy lại toàn bộ pipeline", width="stretch"):
    from src.pipeline import run_pipeline, save_artifacts

    with st.spinner("Đang chạy pipeline 4 tầng…"):
        result = run_pipeline()
        save_artifacts(result)
    st.cache_data.clear()
    st.cache_resource.clear()
    st.success("Hoàn tất!")
    st.rerun()

art = load_artifacts()
if not art:
    st.error(
        "Chưa có kết quả. Hãy chạy `python scripts/run_pipeline.py` "
        "hoặc bấm nút bên trái."
    )
    st.stop()

page = st.sidebar.radio(
    "Trang",
    [
        "🏠 Tổng quan",
        "🧹 Tầng 1 – Tiền xử lý",
        "📊 Tầng 2 – Phân cụm",
        "🛒 Tầng 3 – Luật kết hợp",
        "🎯 Tầng 4 – Gợi ý đa tầng",
        "🧪 Đánh giá mô hình",
    ],
)

summary = art.get("summary", {})

# ── Header ───────────────────────────────────────────────────────────────────
st.title("🛒 HỆ THỐNG PHÂN TÍCH GIỎ HÀNG VÀ GỢI Ý SẢN PHẨM ĐA TẦNG")
st.caption(
    f"Dữ liệu: **{summary.get('n_rows', 0):,}** dòng · "
    f"**{summary.get('n_orders', 0):,}** đơn · "
    f"**{summary.get('n_customers', 0):,}** khách hàng"
)

# ── Trang: Tổng quan ────────────────────────────────────────────────────────
if page == "🏠 Tổng quan":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dòng giao dịch", f"{summary.get('n_rows', 0):,}")
    c2.metric("Đơn hàng", f"{summary.get('n_orders', 0):,}")
    c3.metric("Khách hàng", f"{summary.get('n_customers', 0):,}")
    c4.metric(
        "Kiểm định dữ liệu",
        f"{summary.get('quality_passed', 0)}/{summary.get('quality_total', 0)}",
        delta="đạt",
    )

    cs = summary.get("chi_square") or {}
    cl = summary.get("clustering") or {}
    mba = summary.get("mba") or {}
    st.subheader("Kết quả chính theo từng tầng")
    cols = st.columns(3)
    with cols[0]:
        st.markdown(
            f"**Tầng 1 – Thống kê**\n\n"
            f"- Chi-square `Mã PKKH × Nhóm hàng`: χ² = **{cs.get('chi2', 0):,.2f}**\n"
            f"- p-value = **{cs.get('p_value', 0):.2e}** (< 0,05)\n"
            f"- Cramér's V = **{cs.get('cramers_v', 0):.4f}** → hiệu ứng "
            f"*{cs.get('effect_strength', '')}*"
        )
    with cols[1]:
        sizes = cl.get("sizes", {})
        st.markdown(
            f"**Tầng 2 – Phân cụm**\n\n"
            f"- K chọn = **{cl.get('selected_k', 0)}**\n"
            f"- Silhouette = **{cl.get('silhouette', 0):.4f}**\n"
            f"- Elbow → K = {cl.get('best_k_elbow', 0)}\n"
            f"- Quy mô cụm: {sizes}"
        )
    with cols[2]:
        st.markdown(
            f"**Tầng 3 – Luật kết hợp**\n\n"
            f"- Tổng luật khám phá: **{mba.get('n_rules', 0):,}**\n"
            f"- Luật có Lift > 1: **{mba.get('n_lift_gt_1', 0)}**\n"
            f"- Lift trung bình = **{mba.get('mean_lift', 0):.4f}** (< 1 → hành vi thay thế)"
        )

    st.subheader("Kiến trúc 4 tầng")
    st.markdown(
        """
```
┌─ TẦNG 1: Tiền xử lý & Thống kê ────────────────────────────┐
│  Làm sạch · IQR outlier · Binning · Z-score · Pearson · Chi-square │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌─ TẦNG 2: Phân cụm hành vi ─────────────────────────────────┐
│  RFM (log + Z-score) → K-Means → Elbow & Silhouette          │
│  Đối chiếu Confusion Matrix với Mã PKKH                      │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌─ TẦNG 3: Khai phá luật kết hợp ────────────────────────────┐
│  Apriori → Support/Confidence/Lift/Leverage/Conviction        │
│  Kiểm định Chi-square 2×2 cho từng luật                       │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌─ TẦNG 4: Gợi ý đa tầng ────────────────────────────────────┐
│  Nhánh A (warm)  = Luật MBA ∪ TF-IDF/Cosine ∪ Popularity PKKH │
│  Nhánh B (cold)  = Popularity/Lift theo Mã PKKH               │
│  Nhánh C (fallback) = Best-seller theo nhóm hàng              │
└──────────────────────────────────────────────────────────────┘
```
"""
    )

    chart = CHART_DIR / "chart_01_monthly_revenue.png"
    if chart.exists():
        st.image(str(chart), caption="Doanh thu theo tháng – kiểm chứng mùa vụ Q4")

# ── Trang: Tầng 1 ────────────────────────────────────────────────────────────
elif page == "🧹 Tầng 1 – Tiền xử lý":
    st.subheader("Kiểm định chất lượng dữ liệu")
    tx = art.get("transactions")
    if tx is not None:
        st.write(
            f"**{tx['order_id'].nunique():,}** đơn · "
            f"**{tx['customer_id'].nunique():,}** khách · "
            f"**{tx['item_code'].nunique():,}** mặt hàng · "
            f"**{tx['group_name'].nunique():,}** nhóm hàng"
        )
        st.subheader("Phân phối doanh thu theo nhóm hàng")
        g = tx.groupby("group_name").agg(
            doanh_thu=("amount", "sum"), so_dong=("amount", "size")
        )
        g["tỷ_lệ"] = g["doanh_thu"] / g["doanh_thu"].sum()
        st.bar_chart(g[["doanh_thu"]])
        st.dataframe(g, use_container_width=True)

    cs = summary.get("chi_square") or {}
    if cs:
        st.subheader(f"Chi-square: {cs.get('name', '')}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("χ²", f"{cs.get('chi2', 0):,.2f}")
        c2.metric("p-value", f"{cs.get('p_value', 0):.2e}")
        c3.metric("Cramér's V", f"{cs.get('cramers_v', 0):.4f}")
        c4.metric("Hiệu ứng", cs.get("effect_strength", ""))
        st.info(
            "Kết luận: phân khúc khách hàng **có** ảnh hưởng đến lựa chọn nhóm hàng "
            "(p < 0,05). Tuy nhiên Cramér's V chỉ ở mức *yếu* → mối liên hệ có thật "
            "nhưng không mạnh, cần nhiều tín hiệu hơn để dự đoán."
        )

    chart = CHART_DIR / "chart_05_chi_square_heatmap.png"
    if chart.exists():
        st.image(str(chart), caption="Heatmap chi-square PKKH × Nhóm hàng")

# ── Trang: Tầng 2 ────────────────────────────────────────────────────────────
elif page == "📊 Tầng 2 – Phân cụm":
    cl = summary.get("clustering") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("K được chọn", cl.get("selected_k", 0))
    c2.metric("Silhouette", f"{cl.get('silhouette', 0):.4f}")
    c3.metric("Elbow (knee)", cl.get("best_k_elbow", 0))

    cmp = cl.get("comparison") or {}
    if cmp:
        st.subheader("Đối chiếu với nhãn `Mã PKKH` (Confusion Matrix)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Purity", f"{cmp.get('purity', 0):.4f}")
        c2.metric("Ngưỡng ngẫu nhiên", f"{cmp.get('random_baseline', 0):.4f}")
        c3.metric("Adjusted Rand Index", f"{cmp.get('adjusted_rand_index', 0):.4f}")
        st.warning(
            f"Purity ({cmp.get('purity', 0):.4f}) chỉ nhỉnh hơn ngưỡng ngẫu nhiên "
            f"({cmp.get('random_baseline', 0):.4f}) → **hệ phân khúc hành vi và hệ "
            "phân khúc nhân khẩu học gần như độc lập**. Đây là lý do Tầng 4 phải kết "
            "hợp cả hai tín hiệu."
        )

    prof = art.get("cluster_profile")
    if prof is not None:
        st.subheader("Hồ sơ các cụm")
        st.dataframe(prof, use_container_width=True)

    for name, cap in [
        ("chart_02_elbow_silhouette.png", "Elbow & Silhouette"),
        ("chart_03_confusion_matrix.png", "Confusion Matrix"),
        ("chart_09_rfm_clusters_3d.png", "Không gian RFM 3D"),
    ]:
        p = CHART_DIR / name
        if p.exists():
            st.image(str(p), caption=cap)

# ── Trang: Tầng 3 ───────────────────────────────────────────────────────────
elif page == "🛒 Tầng 3 – Luật kết hợp":
    rules = art.get("rules_exploratory")
    if rules is None:
        rules = art.get("rules")
    if rules is None:
        st.warning("Chưa có dữ liệu luật kết hợp.")
    else:
        st.subheader("Bộ lọc luật")
        c1, c2, c3 = st.columns(3)
        min_lift = c1.slider("Lift tối thiểu", 0.0, 2.0, 0.0, 0.05)
        min_sup = c2.slider("Support tối thiểu", 0.0, 0.2, 0.0, 0.005)
        size = c3.selectbox("Độ dài luật", [2, 3], format_func=lambda x: f"{x} mặt hàng")
        f = rules[
            (rules["lift"] >= min_lift)
            & (rules["support"] >= min_sup)
            & (rules["itemset_size"] == size)
        ]
        st.write(f"**{len(f):,}** luật thỏa điều kiện")
        st.dataframe(
            f.sort_values("lift", ascending=False).head(100),
            use_container_width=True,
        )

        if len(rules):
            n_all = len(rules[rules["itemset_size"] == 2])
            n_gt1 = int((rules[rules["itemset_size"] == 2]["lift"] > 1).sum())
            st.info(
                f"Trên toàn bộ **{n_all}** cặp, chỉ **{n_gt1}** cặp có Lift > 1 "
                f"({n_gt1 / max(n_all, 1):.1%}) → phần lớn các mặt hàng trong cùng giỏ "
                "hàng **thay thế** chứ không bổ trợ."
            )

    tests = art.get("rule_tests")
    if tests is not None and not tests.empty:
        st.subheader("Kiểm định Chi-square 2×2 cho từng luật")
        st.dataframe(tests, use_container_width=True)

    chart = CHART_DIR / "chart_04_lift_distribution.png"
    if chart.exists():
        st.image(str(chart), caption="Phân phối Lift")

# ── Trang: Tầng 4 ────────────────────────────────────────────────────────────
elif page == "🎯 Tầng 4 – Gợi ý đa tầng":
    st.subheader("Gợi ý cho một khách hàng")
    try:
        rec = load_recommender()
    except Exception as exc:
        st.error(f"Không dựng được bộ gợi ý: {exc}")
        rec = None

    if rec is not None:
        c1, c2 = st.columns([1, 2])
        seg_options = ["(tất cả)"] + sorted(set(rec.segments.values()))
        seg = c1.selectbox("Phân khúc `Mã PKKH`", seg_options)
        ctype = c2.radio("Loại khách", ["all", "warm", "cold"], horizontal=True)

        cands = [
            c for c, s in rec.segments.items()
            if (seg == "(tất cả)" or s == seg)
            and (ctype == "all" or rec._is_warm(c) == (ctype == "warm"))
        ]
        if not cands:
            st.info("Không có khách hàng nào thỏa điều kiện.")
        else:
            cust = st.selectbox("Chọn khách hàng", sorted(cands))
            res = rec.recommend(cust)
            b1, b2, b3 = st.columns(3)
            b1.metric("Loại khách", res.customer_type)
            b2.metric("Phân khúc", res.segment_code)
            b3.metric("Nhánh sử dụng", res.branch_used)

            st.markdown("#### Kết quả gợi ý")
            rows = [
                {
                    "Mã SP": r.item_code,
                    "Tên sản phẩm": r.item_name,
                    "Điểm": round(r.score, 4),
                    "Nhánh": r.branch,
                    "Lý do": r.reason,
                }
                for r in res.recommendations
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            hist = rec.history.get(cust, set())
            if hist:
                st.markdown("**Lịch sử mua:** " + ", ".join(sorted(hist)))

    st.subheader("Ma trận Cosine similarity (TF-IDF)")
    chart = CHART_DIR / "chart_08_cosine_similarity.png"
    if chart.exists():
        st.image(str(chart), caption="Tương đồng giữa các mặt hàng")

# ── Trang: Đánh giá ──────────────────────────────────────────────────────────
elif page == "🧪 Đánh giá mô hình":
    st.subheader("Đánh giá trên hold-out theo thời gian")
    st.caption(
        f"Train: trước {CONFIG.evaluation.split_date} · "
        f"Test: từ {CONFIG.evaluation.split_date} · K = {CONFIG.evaluation.k}"
    )
    for key, label in [("eval_warm", "Khách ấm (warm)"), ("eval_cold", "Khách lạnh (cold-start)")]:
        df = art.get(key)
        if df is None:
            continue
        st.markdown(f"#### {label}")
        st.dataframe(df, use_container_width=True, hide_index=True)
        base = df[df["strategy"] == "Random (baseline)"]
        if not base.empty:
            b = base.iloc[0]
            best = df.iloc[0]
            if b["precision_at_k"] > 0:
                gain = (best["precision_at_k"] - b["precision_at_k"]) / b["precision_at_k"]
                st.success(
                    f"Chiến lược tốt nhất **{best['strategy']}**: "
                    f"P@{CONFIG.evaluation.k} = {best['precision_at_k']:.4f} "
                    f"→ **+{gain:.1%}** so với ngẫu nhiên "
                    f"({b['precision_at_k']:.4f}). "
                    f"NDCG@{CONFIG.evaluation.k} = {best['ndcg_at_k']:.4f}."
                )

    chart = CHART_DIR / "chart_06_strategy_comparison.png"
    if chart.exists():
        st.image(str(chart), caption="So sánh các chiến lược gợi ý")

    st.subheader("🔗 API")
    st.code(
        "uvicorn src.api.main:app --reload --port 8000\n"
        "# Swagger UI: http://localhost:8000/docs",
        language="bash",
    )
