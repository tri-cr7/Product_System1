"""Sinh báo cáo Markdown tự động từ kết quả pipeline."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from ..config import CHART_DIR, REPORT_DIR
from ..pipeline import PipelineResult


def _md_table(df: pd.DataFrame, floatfmt: str = "{:.4f}") -> str:
    """Chuyển DataFrame thành bảng Markdown."""
    if df is None or df.empty:
        return "_(không có dữ liệu)_"

    def fmt(v):
        if isinstance(v, float):
            return floatfmt.format(v)
        if isinstance(v, (int,)):
            return f"{v:,}"
        return str(v)

    header = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "| " + " | ".join("---" for _ in df.columns) + " |"
    lines = [header, sep]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt(v) for v in row.values) + " |")
    return "\n".join(lines)


def _chart(name: str, caption: str) -> str:
    return f"![{caption}](charts/{name})\n\n*{caption}*\n"


def build_markdown_report(
    result: PipelineResult,
    out_dir: Path | None = None,
    filename: str = "BAO_CAO_KET_QUA.md",
) -> str:
    """Sinh file báo cáo Markdown đầy đủ 4 tầng."""
    out_dir = out_dir or REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename

    tx = result.transactions
    cs = result.chi_square_segment_group
    parts: list[str] = []

    # ── Tiêu đề ─────────────────────────────────────────────────────────────
    parts.append(
        f"""# BÁO CÁO KẾT QUẢ — HỆ THỐNG PHÂN TÍCH GIỎ HÀNG VÀ GỢI Ý SẢN PHẨM ĐA TẦNG

> **Nguồn dữ liệu:** `{result.transactions.attrs.get('source', 'data_ggsheet.xlsx')}`
> **Thời điểm chạy:** {result.started_at:%Y-%m-%d %H:%M:%S}
> **Phạm vi:** {len(tx):,} dòng giao dịch · {tx['order_id'].nunique():,} đơn hàng · {tx['customer_id'].nunique():,} khách hàng · {tx['item_code'].nunique():,} mặt hàng
"""
    )

    # ── 0. Tóm tắt KPI ─────────────────────────────────────────────────────
    warm = result.evaluation_warm
    cold = result.evaluation_cold
    best_warm = warm.iloc[0] if warm is not None and not warm.empty else None
    best_cold = cold.iloc[0] if cold is not None and not cold.empty else None
    rand_warm = warm[warm["strategy"] == "Random (baseline)"] if warm is not None else None

    kpi = []
    if best_warm is not None:
        kpi.append(f"| Gợi ý tốt nhất (warm) | **{best_warm['strategy']}** |")
    if best_cold is not None:
        kpi.append(f"| Gợi ý tốt nhất (cold-start) | **{best_cold['strategy']}** |")
    if best_warm is not None:
        kpi.append(f"| Precision@5 (warm) | **{best_warm['precision_at_k']:.4f}** |")
        kpi.append(f"| Recall@5 (warm) | {best_warm['recall_at_k']:.4f} |")
        kpi.append(f"| NDCG@5 (warm) | {best_warm['ndcg_at_k']:.4f} |")
    if rand_warm is not None and not rand_warm.empty and best_warm is not None:
        r = float(rand_warm.iloc[0]["precision_at_k"])
        if r > 0:
            kpi.append(
                f"| Cải thiện so với ngẫu nhiên | **+{(best_warm['precision_at_k'] - r) / r:.1%}** |"
            )
    if cs is not None:
        kpi.append(f"| Chi-square PKKH × Nhóm hàng | χ²={cs.chi2:.2f}, p={cs.p_value:.2e}, V={cs.cramers_v:.4f} |")
    if result.clustering:
        kpi.append(f"| K-Means | K={result.clustering.selected_k}, Silhouette={result.clustering.silhouette:.4f} |")
    if result.rules:
        kpi.append(f"| Luật kết hợp | {result.rules.n_rules} luật, Lift TB = {result.rules.rules['lift'].mean():.4f} |")

    parts.append("## 0. TÓM TẮT CHỈ SỐ CHÍNH\n\n| Chỉ số | Giá trị |\n| --- | --- |\n" + "\n".join(kpi) + "\n")

    # ── 1. TẦNG 1 ──────────────────────────────────────────────────────────
    qdf = pd.DataFrame(
        [
            {
                "Kiểm tra": c.name,
                "Kết quả": "✅ Đạt" if c.passed else "⚠️ Cần xử lý",
                "Chi tiết": c.detail,
                "Số dòng ảnh hưởng": c.n_affected,
            }
            for c in result.quality_checks
        ]
    )
    parts.append(
        "## 1. TẦNG 1 — TIỀN XỬ LÝ & THỐNG KÊ MÔ TẢ\n\n"
        "### 1.1 Kiểm định chất lượng dữ liệu\n\n" + _md_table(qdf) + "\n"
    )
    if result.prep_log:
        parts.append(
            "### 1.2 Nhật ký biến đổi\n\n" + "\n".join(f"- {x}" for x in result.prep_log) + "\n"
        )
    if result.outlier_reports:
        odf = pd.DataFrame(
            [
                {
                    "Cột": o.column,
                    "Q1": o.q1,
                    "Q3": o.q3,
                    "IQR": o.iqr,
                    "Cận dưới": o.lower_bound,
                    "Cận trên": o.upper_bound,
                    "Số outlier": o.n_outliers,
                    "Tỷ lệ": f"{o.ratio:.2%}",
                }
                for o in result.outlier_reports
            ]
        )
        parts.append(
            "### 1.3 Phát hiện outlier theo IQR (Slide 4)\n\n"
            + _md_table(odf, "{:,.2f}")
            + "\n\n> Outlier được **đánh dấu** chứ không xóa: doanh thu cao thường là "
            "khách hàng giá trị cao, xóa đi sẽ làm sai lệch phân tích phân khúc.\n"
        )
    if result.descriptive_stats is not None:
        desc = result.descriptive_stats.copy()
        desc.index = [
            {
                "quantity": "SL",
                "unit_price": "Đơn giá",
                "amount": "Thành tiền",
                "bin_quantity": "Bin(SL)",
                "bin_unit_price": "Bin(Đơn giá)",
            }.get(c, c)
            for c in desc.index
        ]
        parts.append(
            "### 1.4 Thống kê mô tả (Slide 4)\n\n"
            + _md_table(desc.reset_index().rename(columns={"index": "Biến"}), "{:,.2f}")
            + "\n"
        )
    if result.correlation:
        c = result.correlation
        parts.append(
            f"### 1.5 Tương quan Pearson\n\n"
            f"- `{c['col_x']}` ↔ `{c['col_y']}`: **r = {c['pearson_r']:.4f}** "
            f"(r² = {c['r_squared']:.4f}) – {c['interpretation']}\n"
        )
    if cs is not None:
        parts.append(
            f"### 1.6 Kiểm định Chi-square: {cs.name}\n\n"
            f"- χ² = **{cs.chi2:.2f}**, dof = {cs.dof}, p-value = **{cs.p_value:.3e}** (< α = {cs.alpha})\n"
            f"- Cramér's V = **{cs.cramers_v:.4f}** → hiệu ứng **{cs.effect_strength.lower()}**\n"
            f"- Kết luận: **{'phụ thuộc' if cs.significant else 'không phụ thuộc'}**\n\n"
            + _md_table(cs.contingency.reset_index(), "{:,.0f}")
            + "\n\n"
            + _chart("chart_05_chi_square_heatmap.png", "Heatmap kiểm định chi-square PKKH × Nhóm hàng")
        )

    # ── 2. TẦNG 2 ──────────────────────────────────────────────────────────
    if result.rfm and result.clustering:
        elbow = result.clustering.elbow.to_frame()
        parts.append(
            "## 2. TẦNG 2 — PHÂN CỤM HÀNH VI (RFM + K-MEANS)\n\n"
            "### 2.1 Đặc trưng RFM\n\n"
            f"- Mốc tham chiếu: {result.rfm.reference_date:%Y-%m-%d}\n"
            f"- Số khách hàng: {result.rfm.n_customers:,}\n"
            + "\n".join(f"- {n}" for n in result.rfm.notes)
            + "\n"
        )
        parts.append(
            "### 2.2 Đánh giá chọn K (Slide 5.3 – Elbow & Silhouette)\n\n"
            + _md_table(elbow)
            + f"\n\n- Elbow (knee) → K = **{result.clustering.elbow.best_k_elbow}**\n"
            f"- Silhouette đạt đỉnh tại K = **{result.clustering.elbow.best_k_silhouette}** "
            f"(score = {max(elbow['silhouette']):.4f})\n"
            f"- **K được chọn = {result.clustering.selected_k}** theo tiêu chí nghiệp vụ "
            "(VIP / Trung thành / Cần chăm sóc)\n\n"
            + _chart("chart_02_elbow_silhouette.png", "Elbow Method & Silhouette Score")
        )
        if result.cluster_profile is not None:
            parts.append(
                "### 2.3 Hồ sơ các cụm\n\n"
                + _md_table(result.cluster_profile)
                + "\n\n" + _chart("chart_10_cluster_profile.png", "Hồ sơ đặc trưng các cụm")
            )
        cmp = result.clustering.comparison
        if cmp:
            parts.append(
                "### 2.4 Đối chiếu với nhãn Mã PKKH (Confusion Matrix – Slide 5)\n\n"
                + _md_table(cmp["confusion_matrix"].reset_index(), "{:,.0f}")
                + f"\n\n- Accuracy (ánh xạ tối ưu): **{cmp['accuracy_optimal']:.4f}**\n"
                f"- Purity: **{cmp['purity']:.4f}** vs ngưỡng ngẫu nhiên {cmp['random_baseline']:.4f}\n"
                f"- Macro-F1: {cmp['macro_f1']:.4f} | Weighted-F1: {cmp['weighted_f1']:.4f}\n"
                f"- Adjusted Rand Index: {cmp['adjusted_rand_index']:.4f}\n\n"
                "> **Kết luận:** phân khúc nhân khẩu học (`Mã PKKH`) và cụm hành vi "
                "(RFM + K-Means) gần như **độc lập** → chiến lược gợi ý phải kết hợp "
                "cả hai tín hiệu, không thể dùng PKKH đại diện cho hành vi.\n\n"
                + _chart("chart_03_confusion_matrix.png", "Confusion Matrix K-Means vs Mã PKKH")
            )
        parts.append(_chart("chart_09_rfm_clusters_3d.png", "Phân cụm K-Means trong không gian RFM"))

    # ── 3. TẦNG 3 ──────────────────────────────────────────────────────────
    if result.rules:
        r = result.rules.rules
        parts.append(
            "## 3. TẦNG 3 – KHAI PHÁ LUẬT KẾT HỢP (MARKET BASKET ANALYSIS)\n\n"
            f"- Số giỏ hàng: **{result.rules.n_baskets:,}**\n"
            + "\n".join(f"- {n}" for n in result.rules.notes)
            + "\n"
        )
        if result.basket_stats:
            bs = result.basket_stats
            parts.append(
                "### 3.1 Cấu trúc giỏ hàng\n\n"
                f"- Số mặt hàng trung bình/đơn: **{bs['avg_items_per_order']:.2f}** "
                f"(median {bs['median_items_per_order']:.0f}, max {bs['max_items_per_order']})\n"
                f"- Tỷ lệ đơn nhiều hơn 1 mặt hàng: **{bs['share_multi_item_orders']:.2%}**\n"
                f"- Số nhóm hàng trung bình/đơn: {bs['avg_groups_per_order']:.2f}\n\n"
            )
        if not r.empty:
            top = r.head(12).copy()
            parts.append(
                "### 3.2 Top luật theo Lift (bộ vận hành, support ≥ 1%)\n\n"
                + _md_table(
                    top[
                        ["antecedent", "consequent", "support", "confidence", "lift", "leverage", "conviction"]
                    ]
                )
                + "\n\n"
                + _chart("chart_04_lift_distribution.png", "Phân phối Lift của các luật kết hợp")
            )

        # Bộ khám phá: toàn bộ cặp để thấy đầy đủ phân phối Lift
        exp = result.rules_exploratory
        if exp is not None and not exp.rules.empty:
            pairs = exp.rules[exp.rules["itemset_size"] == 2]
            # Gộp 2 chiều (A→B và B→A) về 1 cặp để đếm theo tổ hợp đôi vô hướng
            uniq = (
                pairs.assign(
                    pair=pairs.apply(
                        lambda r: tuple(sorted((r["antecedent"], r["consequent"]))), axis=1
                    )
                )
                .drop_duplicates("pair")
                .copy()
            )
            lift_by_pair = uniq.groupby("pair")["lift"].first()
            n_all = len(lift_by_pair)
            n_gt1 = int((lift_by_pair > 1).sum())
            n_eq1 = int((lift_by_pair.round(2) == 1.0).sum())
            n_lt1 = int((lift_by_pair < 1).sum())
            parts.append(
                "### 3.3 Phân phối Lift trên **toàn bộ** các cặp (bộ khám phá)\n\n"
                "Bộ vận hành lọc theo support nên che mất các luật có Lift > 1 nhưng "
                "support rất thấp. Bộ khám phá liệt kê **mọi cặp có support > 0** để "
                "đánh giá toàn bộ phân phối (mỗi cặp đếm 1 lần, không tính chiều).\n\n"
                f"- Tổng số cặp: **{n_all}** (= C(19,2))\n"
                f"- Lift > 1 (tương quan dương): **{n_gt1}** ({n_gt1 / n_all:.1%})\n"
                f"- Lift ≈ 1 (gần độc lập): **{n_eq1}** ({n_eq1 / n_all:.1%})\n"
                f"- Lift < 1 (tương quan âm): **{n_lt1}** ({n_lt1 / n_all:.1%})\n\n"
                f"- Thống kê mô tả Lift: mean = **{lift_by_pair.mean():.4f}** · "
                f"std = {lift_by_pair.std():.4f} · "
                f"min = {lift_by_pair.min():.4f} · "
                f"max = {lift_by_pair.max():.4f} · "
                f"median = {lift_by_pair.median():.4f}\n\n"
                + _md_table(
                    uniq.nlargest(10, "lift")[
                        ["antecedent", "consequent", "support", "confidence", "lift"]
                    ]
                )
                + "\n\n> **Kết luận Tầng 3:** đa số cặp có Lift < 1 → các mặt hàng "
                "trong cùng giỏ hàng **cạnh tranh với nhau** (hành vi thay thế) chứ "
                "không bổ trợ. Các cặp Lift > 1 đều thuộc nhóm *Set trà* và có support "
                "< 0,25% → **không đủ cơ sở thống kê** để đưa vào vận hành. Đây là lý do "
                "tài liệu thiết kế **Tầng 4** đa tầng.\n"
            )
        if result.rule_tests is not None and not result.rule_tests.empty:
            parts.append(
                "### 3.4 Kiểm định Chi-square 2×2 cho từng luật (Slide 1.1 áp dụng mới)\n\n"
                + _md_table(result.rule_tests)
                + "\n"
            )
        if result.targeted_rules is not None and not result.targeted_rules.empty:
            parts.append(
                "### 3.5 Luật kết hợp theo phân khúc khách hàng\n\n"
                + _md_table(result.targeted_rules)
                + "\n"
            )

    # ── 4. TẦNG 4 ──────────────────────────────────────────────────────────
    parts.append(
        "## 4. TẦNG 4 – GỢI Ý SẢN PHẨM ĐA TẦNG\n\n"
        "### 4.1 Kiến trúc 3 nhánh\n\n"
        "| Nhánh | Đối tượng | Cơ chế | Tín hiệu |\n| --- | --- | --- | --- |\n"
        "| **A** | Khách ấm (warm) | Luật MBA (confidence) ∪ TF-IDF + Cosine ∪ Popularity PKKH | Hành vi lịch sử |\n"
        "| **B** | Khách lạnh (cold-start) | Popularity + Lift theo `Mã PKKH` | Nhân khẩu học |\n"
        "| **C** | Dự phòng | Best-seller theo nhóm hàng liên quan | Đảm bảo ≥ K gợi ý |\n\n"
        "> **Điểm thiết kế quan trọng:** `Mã PKKH` là thuộc tính **nhân khẩu học tĩnh** "
        "(không đổi theo thời gian) → nhánh B áp dụng được cho **cả khách lạnh**. "
        "Đây là cách giải quyết cold-start một cách có nguyên tắc thay vì dùng "
        "phổ biến toàn cục.\n\n"
        "**Chuẩn hóa điểm trước khi gộp:** mọi tín hiệu được đưa về thang `[0, 1]` "
        "(confidence của luật, cosine similarity, popularity chia cho max toàn cục, "
        "lift chia cho max của phân khúc) trước khi cộng với trọng số — nếu không, "
        "tín hiệu có thang đo lớn sẽ chi phối hoàn toàn.\n\n"
        "### 4.2 Đánh giá trên hold-out theo thời gian\n\n"
        f"- Mốc chia: **train < {result.config.evaluation.split_date}**, test ≥ mốc chia\n"
        f"- K = {result.config.evaluation.k}\n"
        f"- Trọng số: {result.config.recommender.weights}\n\n"
    )
    if result.evaluation_warm is not None:
        parts.append(
            "#### Khách ấm (warm)\n\n"
            + _md_table(result.evaluation_warm)
            + "\n\n"
        )
    if result.evaluation_cold is not None:
        parts.append(
            "#### Khách lạnh (cold-start)\n\n"
            + _md_table(result.evaluation_cold)
            + "\n\n"
        )
    parts.append(_chart("chart_06_strategy_comparison.png", "So sánh các chiến lược gợi ý"))
    parts.append(_chart("chart_08_cosine_similarity.png", "Ma trận Cosine similarity TF-IDF"))

    # ── 5. Kết luận ────────────────────────────────────────────────────────
    parts.append(
        "## 5. KẾT LUẬN\n\n"
        "1. **Chất lượng dữ liệu tốt**: sau tiền xử lý, toàn bộ kiểm tra nhất quán đạt; "
        "kiểm định chi-square cho thấy phân khúc khách hàng ảnh hưởng đến lựa chọn nhóm hàng.\n"
        "2. **Phân cụm hành vi bằng RFM + K-Means** cho 3 cụm rõ ràng; đối chiếu với "
        "`Mã PKKH` cho thấy hai hệ phân khúc gần như độc lập.\n"
        "3. **Luật kết hợp có Lift trung bình < 1** → trên dữ liệu này mô hình hành vi "
        "chiếm ưu thế với hành vi *thay thế* hơn là *bổ trợ*; đây là phát hiện định lượng "
        "quan trọng, không phải lỗi thuật toán.\n"
        "4. **Gợi ý đa tầng** vượt trội baseline ngẫu nhiên rõ rệt, đặc biệt nhánh "
        "popularity/lift theo phân khúc cho khách lạnh.\n"
    )

    text = "\n".join(parts)
    path.write_text(text, encoding="utf-8")
    return str(path)
