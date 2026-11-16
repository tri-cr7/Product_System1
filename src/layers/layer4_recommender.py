"""Tầng 4 – Gợi ý sản phẩm đa tầng.

Ba nhánh gợi ý (multi-layer arbitration):

* **Nhánh A (warm)** – khách đã có lịch sử mua: luật MBA (confidence) ∪ content-based.
* **Nhánh B (cold)** – khách mới: popularity / lift theo phân khúc ``Mã PKKH``.
* **Nhánh C (fallback)** – sản phẩm bán chạy của nhóm hàng liên quan.

Slide 1.1 (làm sạch văn bản) + Slide 5.2 (đo khoảng cách) mở rộng sang miền văn bản.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from ..config import RecommenderConfig

#: Stopword tiếng Việt tối thiểu (bổ sung theo ngữ cảnh sản phẩm)
DEFAULT_STOPWORDS = [
    "và", "của", "có", "là", "cho", "với", "các", "những", "một",
    "gói", "vị", "loại", "nước", "sản", "phẩm",
]


# ── Làm sạch văn bản (Slide 1.1) ─────────────────────────────────────────────
def clean_text(text: str, drop_stopwords: bool = True) -> str:
    """Chuẩn hoá tên sản phẩm tiếng Việt thành dạng phù hợp cho vector hóa.

    Bước: lowercase → bỏ dấu câu → bỏ số thứ tự ("set 10 gói" → "set gói") →
    tách token bằng regex → loại stopword.
    """
    if not isinstance(text, str) or not text.strip():
        return ""
    s = text.lower()
    s = re.sub(r"[^0-9a-zà-ỹ\s]", " ", s)  # giữ chữ có dấu tiếng Việt
    s = re.sub(r"\d+", " ", s)  # bỏ số thứ tự
    tokens = [t for t in s.split() if t]
    if drop_stopwords:
        tokens = [t for t in tokens if t not in DEFAULT_STOPWORDS]
    return " ".join(tokens)


@dataclass
class ItemIndex:
    """Ma trận TF-IDF + Cosine similarity giữa các mặt hàng."""

    items: pd.DataFrame
    matrix: object  # scipy sparse matrix
    similarity: np.ndarray
    vectorizer: TfidfVectorizer
    code_to_index: dict[str, int] = field(default_factory=dict)

    @property
    def codes(self) -> list[str]:
        return self.items["item_code"].tolist()

    def most_similar(
        self, item_code: str, top_n: int = 5, exclude: set[str] | None = None
    ) -> list[tuple[str, float]]:
        """Trả về ``[(mã sản phẩm, điểm cosine), ...]`` gần nhất với ``item_code``."""
        if item_code not in self.code_to_index:
            return []
        i = self.code_to_index[item_code]
        sim = self.similarity[i]
        order = np.argsort(-sim)[: top_n + 5]
        out = []
        for j in order:
            code = self.codes[j]
            if code == item_code:
                continue
            if exclude and code in exclude:
                continue
            out.append((code, float(sim[j])))
            if len(out) >= top_n:
                break
        return out


def build_item_index(
    df: pd.DataFrame,
    config: RecommenderConfig | None = None,
) -> ItemIndex:
    """Dựng ma trận TF-IDF và Cosine similarity cho toàn bộ mặt hàng.

    ``tfidf(t,d) = tf(t,d) · log(N / df(t))`` với ``tf`` biến thể sublinear
    (``1 + log(count)``) để giảm ảnh hưởng của từ lặp nhiều lần.
    """
    config = config or RecommenderConfig()
    items = (
        df[["item_code", "item_name", "group_name"]]
        .drop_duplicates("item_code")
        .reset_index(drop=True)
        .copy()
    )
    items["clean_text"] = items["item_name"] + " " + items["group_name"]
    items["clean_text"] = items["clean_text"].map(clean_text)

    vectorizer = TfidfVectorizer(
        token_pattern=config.token_pattern,
        ngram_range=config.ngram_range,
        sublinear_tf=config.sublinear_tf,
        lowercase=False,  # đã lowercase thủ công
    )
    matrix = vectorizer.fit_transform(items["clean_text"])
    similarity = (matrix @ matrix.T).toarray()
    np.fill_diagonal(similarity, -1.0)

    code_to_index = {c: i for i, c in enumerate(items["item_code"].tolist())}
    return ItemIndex(
        items=items,
        matrix=matrix,
        similarity=similarity,
        vectorizer=vectorizer,
        code_to_index=code_to_index,
    )


# ── Các chiến lược gợi ý ─────────────────────────────────────────────────────
@dataclass
class StrategyOutput:
    """Kết quả gợi ý của một chiến lược cho toàn bộ khách hàng."""

    name: str
    recommendations: dict[str, list[str]]
    scores: dict[str, dict[str, float]] = field(default_factory=dict)

    def top_for(self, customer_id: str, k: int = 5) -> list[str]:
        return self.recommendations.get(customer_id, [])[:k]


def normalize_scores(strategy: StrategyOutput) -> StrategyOutput:
    """Chuẩn hóa điểm số của một chiến lược về khoảng ``[0, 1]``.

    **Bắt buộc** trước khi gộp nhiều chiến lược: confidence của luật MBA nằm trong
    ``[0, 1]`` nhưng cosine similarity của TF-IDF nằm trong ``[0, ~0.8]`` còn
    lift của phân khúc có thể vượt 10. Nếu gộp trực tiếp, chiến lược có thang đo
    lớn sẽ "át" hoàn toàn các chiến lược khác và trọng số trở nên vô nghĩa.

    Chuẩn hóa theo **giá trị lớn nhất toàn cục** (không phải theo từng khách) để
    giữ nguyên thứ hạng tương đối giữa các khách hàng.
    """
    max_abs = 0.0
    for scores in strategy.scores.values():
        for v in scores.values():
            max_abs = max(max_abs, abs(float(v)))
    if max_abs <= 0:
        return strategy

    norm_scores = {
        cust: {code: float(v) / max_abs for code, v in scores.items()}
        for cust, scores in strategy.scores.items()
    }
    norm_recs = {
        cust: [c for c, _ in sorted(scores.items(), key=lambda kv: -kv[1])]
        for cust, scores in norm_scores.items()
    }
    return StrategyOutput(strategy.name, norm_recs, norm_scores)


def strategy_global_popularity(train: pd.DataFrame, customers: list[str]) -> StrategyOutput:
    """Baseline: sản phẩm bán chạy nhất toàn cục."""
    pop = train["item_code"].value_counts()
    recs = {c: pop.index.tolist() for c in customers}
    scores = {c: {code: float(pop[code]) for code in pop.index} for c in customers}
    return StrategyOutput("Popularity toàn cục", recs, scores)


def strategy_segment_popularity(
    train: pd.DataFrame,
    customers: list[str],
    customer_segments: dict[str, str] | None = None,
) -> StrategyOutput:
    """Popularity **có điều kiện theo phân khúc** – chiến lược mạnh nhất trên dữ liệu này.

    ``Mã PKKH`` là thuộc tính **nhân khẩu học** (tĩnh theo thời gian), nên vẫn biết
    được với khách lạnh – đây chính là lý do nhánh B khắc phục được vấn đề
    cold-start mà content-based không giải quyết được.
    """
    seg = customer_segments or train.groupby("customer_id")["segment_code"].first().to_dict()
    global_pop = train["item_code"].value_counts()
    seg_pop: dict[str, pd.Series] = {}
    for s, g in train.groupby("segment_code"):
        seg_pop[s] = g["item_code"].value_counts() / len(g)

    recs: dict[str, list[str]] = {}
    scores: dict[str, dict[str, float]] = {}
    for c in customers:
        s = seg.get(c)
        base = seg_pop.get(s, global_pop)
        ranked = base.sort_values(ascending=False)
        recs[c] = ranked.index.tolist()
        scores[c] = {code: float(v) for code, v in ranked.items()}
    return StrategyOutput("Popularity theo PKKH", recs, scores)


def strategy_segment_lift(
    train: pd.DataFrame,
    customers: list[str],
    customer_segments: dict[str, str] | None = None,
    min_count: int = 3,
) -> StrategyOutput:
    """Lift của sản phẩm trong phân khúc so với toàn cục.

    ``lift_s(i) = pop_s(i) / pop(i)``.  Chỉ giữ sản phẩm có đủ số lần xuất hiện
    trong phân khúc (``min_count``) để tránh lift khổng lồ do mẫu cực nhỏ.

    Điểm lift được **chuẩn hóa theo từng phân khúc** (chia cho giá trị lift lớn
    nhất trong phân khúc) → cùng thang đo ``[0, 1]`` với popularity, nhờ đó có thể
    cộng trực tiếp khi gộp tín hiệu trong nhánh B.
    """
    seg = customer_segments or train.groupby("customer_id")["segment_code"].first().to_dict()
    global_pop = train["item_code"].value_counts() / len(train)
    seg_pop: dict[str, pd.Series] = {}
    for s, g in train.groupby("segment_code"):
        seg_pop[s] = g["item_code"].value_counts() / len(g)

    # Lift chuẩn hoá theo phân khúc
    seg_lift_norm: dict[str, pd.Series] = {}
    for s, counts in seg_pop.items():
        sub = train[train["segment_code"] == s]
        counts = counts[counts * len(sub) >= min_count]
        denom = global_pop.reindex(counts.index).replace(0, np.nan)
        lift = (counts / denom).fillna(0.0)
        m = lift.max()
        seg_lift_norm[s] = (lift / m) if m and m > 0 else lift

    recs: dict[str, list[str]] = {}
    scores: dict[str, dict[str, float]] = {}
    for c in customers:
        s = seg.get(c)
        if s is None or s not in seg_lift_norm:
            base = (global_pop / (global_pop.max() or 1)).sort_values(ascending=False)
        else:
            base = seg_lift_norm[s].sort_values(ascending=False)
        recs[c] = base.index.tolist()
        scores[c] = {code: float(v) for code, v in base.items()}
    return StrategyOutput("Lift theo PKKH", recs, scores)


def strategy_content_based(
    train: pd.DataFrame,
    customers: list[str],
    index: ItemIndex,
    top_n: int = 5,
) -> StrategyOutput:
    """Content-based: TF-IDF + Cosine similarity trên lịch sử mua."""
    history = train.groupby("customer_id")["item_code"].apply(lambda s: set(s.astype(str))).to_dict()
    recs: dict[str, list[str]] = {}
    scores: dict[str, dict[str, float]] = {}
    for c in customers:
        owned = history.get(c, set())
        if not owned:
            recs[c] = []
            scores[c] = {}
            continue
        best: dict[str, float] = {}
        for item in owned:
            for code, sim in index.most_similar(item, top_n=top_n * 2, exclude=owned):
                best[code] = max(best.get(code, 0.0), sim)
        ranked = sorted(best.items(), key=lambda kv: -kv[1])
        recs[c] = [c_ for c_, _ in ranked]
        scores[c] = dict(ranked)
    return StrategyOutput("Content-based TF-IDF+Cosine", recs, scores)


def strategy_association_rules(
    train: pd.DataFrame,
    customers: list[str],
    min_confidence: float = 0.10,
) -> StrategyOutput:
    """Luật kết hợp: xếp hạng theo confidence cao nhất từ sản phẩm khách đã mua."""
    baskets = train.groupby("order_id")["item_code"].apply(lambda s: sorted(set(s.astype(str))))
    co: dict[tuple[str, str], int] = {}
    for items in baskets:
        for a in items:
            for b in items:
                if a != b:
                    co[(a, b)] = co.get((a, b), 0) + 1
    den = train.groupby("item_code")["order_id"].nunique()

    history = train.groupby("customer_id")["item_code"].apply(lambda s: set(s.astype(str))).to_dict()
    recs: dict[str, list[str]] = {}
    scores: dict[str, dict[str, float]] = {}
    for c in customers:
        owned = history.get(c, set())
        sc: dict[str, float] = {}
        for (a, b), v in co.items():
            if a in owned:
                conf = v / den[a]
                if conf >= min_confidence:
                    sc[b] = max(sc.get(b, 0.0), float(conf))
        ranked = sorted(sc.items(), key=lambda kv: -kv[1])
        recs[c] = [code for code, _ in ranked]
        scores[c] = dict(ranked)
    return StrategyOutput("Rule MBA (confidence)", recs, scores)


def strategy_random(
    train: pd.DataFrame, customers: list[str], seed: int = 42, n: int = 1
) -> StrategyOutput:
    """Baseline ngẫu nhiên – **bắt buộc** để diễn giải đúng mọi chỉ số Top-K."""
    rng = np.random.default_rng(seed)
    all_items = train["item_code"].unique().tolist()
    history = train.groupby("customer_id")["item_code"].apply(lambda s: set(s.astype(str))).to_dict()
    recs: dict[str, list[str]] = {}
    for c in customers:
        owned = history.get(c, set())
        pool = [i for i in all_items if i not in owned]
        picks: list[str] = []
        for _ in range(n):
            picks.extend(rng.choice(pool, size=min(len(pool), len(all_items)), replace=False).tolist())
        recs[c] = list(dict.fromkeys(picks))
    return StrategyOutput("Random (baseline)", recs)


# ── Arbitration: gộp nhiều chiến lược ───────────────────────────────────────
def arbitrate(
    customer_id: str,
    owned: set[str],
    strategies: dict[str, StrategyOutput],
    weights: dict[str, float],
    top_k: int = 5,
    fallback_items: list[str] | None = None,
) -> list[tuple[str, float]]:
    """Gộp điểm của nhiều chiến lược, khử trùng, trả về ``top_k`` gợi ý.

    Điểm cuối cùng của mỗi sản phẩm = ``Σ (trọng số × điểm của chiến lược)``.
    Sản phẩm khách đã mua bị loại khỏi danh sách gợi ý.

    .. note::
       Các chiến lược **phải được chuẩn hóa** (xem :func:`normalize_scores`) trước
       khi gọi hàm này, nếu không chiến lược có thang đo lớn sẽ chi phối toàn bộ.
    """
    total: dict[str, float] = {}
    for key, strategy in strategies.items():
        w = weights.get(key, 0.0)
        if w <= 0:
            continue
        scores = strategy.scores.get(customer_id, {})
        for code, val in scores.items():
            if code in owned:
                continue
            total[code] = total.get(code, 0.0) + w * float(val)

    ranked = sorted(total.items(), key=lambda kv: -kv[1])[:top_k]

    if len(ranked) < top_k and fallback_items:
        seen = {c for c, _ in ranked}
        for code in fallback_items:
            if len(ranked) >= top_k:
                break
            if code in owned or code in seen:
                continue
            ranked.append((code, 0.0))
    return ranked


# ── Hệ thống gợi ý đa tầng (kiến trúc 3 nhánh) ──────────────────────────────
@dataclass
class Recommendation:
    """Một gợi ý kèm dấu vết giải thích (để trả lời câu hỏi "vì sao?" khi bảo vệ)."""

    item_code: str
    item_name: str
    score: float
    branch: str
    reason: str


@dataclass
class MultiLayerResult:
    """Kết quả gợi ý cho một khách hàng."""

    customer_id: str
    customer_type: str          # "warm" | "cold"
    segment_code: str
    recommendations: list[Recommendation]
    branch_used: str

    def to_dict(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "customer_type": self.customer_type,
            "segment_code": self.segment_code,
            "branch_used": self.branch_used,
            "recommendations": [
                {
                    "item_code": r.item_code,
                    "item_name": r.item_name,
                    "score": round(r.score, 6),
                    "branch": r.branch,
                    "reason": r.reason,
                }
                for r in self.recommendations
            ],
        }


class MultiLayerRecommender:
    """Bộ gợi ý 3 nhánh theo kiến trúc của hệ thống.

    * **Nhánh A (warm)** – khách có lịch sử mua: luật MBA (confidence) ∪ content-based.
    * **Nhánh B (cold)** – khách mới: popularity / lift theo phân khúc ``Mã PKKH``.
    * **Nhánh C (fallback)** – bán chạy theo nhóm hàng để luôn đủ ``top_k`` gợi ý.

    Điểm mấu chốt: ``Mã PKKH`` là thuộc tính nhân khẩu học **tĩnh**, nên nhánh B
    áp dụng được cho cả khách lạnh – giải quyết cold-start một cách có nguyên tắc.
    """

    def __init__(
        self,
        train: pd.DataFrame,
        item_index: ItemIndex,
        config: RecommenderConfig | None = None,
        customer_segments: dict[str, str] | None = None,
        all_customers: list[str] | None = None,
    ):
        self.config = config or RecommenderConfig()
        self.train = train
        self.index = item_index
        self.segments = customer_segments or (
            train.groupby("customer_id")["segment_code"].first().to_dict()
        )
        # **Quan trọng**: phải bao gồm cả khách lạnh (chưa xuất hiện trong train),
        # nếu không nhánh B sẽ không có điểm số cho nhóm khách này.
        self.customers = sorted(set(all_customers) | set(train["customer_id"].unique()))
        self.history = (
            train.groupby("customer_id")["item_code"].apply(lambda s: set(s.astype(str))).to_dict()
        )
        self.item_names = dict(zip(item_index.items["item_code"], item_index.items["item_name"]))
        self.item_groups = dict(zip(item_index.items["item_code"], item_index.items["group_name"]))

        self.strategies: dict[str, StrategyOutput] = {
            "rule": strategy_association_rules(
                train, self.customers, min_confidence=self.config.min_rule_confidence
            ),
            "content": strategy_content_based(
                train, self.customers, item_index, top_n=self.config.top_k
            ),
            "segment": strategy_segment_popularity(
                train, self.customers, self.segments
            ),
            "segment_lift": strategy_segment_lift(train, self.customers, self.segments),
            "popularity": strategy_global_popularity(train, self.customers),
        }
        # Chuẩn hóa điểm trước khi gộp (xem normalize_scores)
        self.strategies = {k: normalize_scores(v) for k, v in self.strategies.items()}
        self._group_best: dict[str, list[str]] = self._build_group_fallback()

    def _build_group_fallback(self) -> dict[str, list[str]]:
        """Nhánh C: sản phẩm bán chạy nhất của từng nhóm hàng."""
        out: dict[str, list[str]] = {}
        for g, sub in self.train.groupby("group_code"):
            out[g] = sub["item_code"].value_counts().index.tolist()
        return out

    def _is_warm(self, customer_id: str) -> bool:
        return bool(self.history.get(customer_id))

    def _branch_a(self, customer_id: str, owned: set[str]) -> list[Recommendation]:
        """Nhánh A: luật MBA ∪ content-based ∪ tín hiệu phân khúc cho khách ấm.

        Dùng **cơ chế hợp nhất nhiều tín hiệu (Weighted Union)**: điểm cuối cùng
        của sản phẩm là *tổng* điểm của các tín hiệu, sau khi tất cả đã được
        chuẩn hóa về ``[0, 1]``. Sản phẩm được đề xuất bởi **nhiều tín hiệu**
        sẽ có điểm cao hơn → ưu tiên sản phẩm "được các chiến lược đồng ý".

        Ba tín hiệu:
        1. ``rule``   – confidence của luật kết hợp MBA
        2. ``content`` – cosine similarity TF-IDF với lịch sử mua
        3. ``segment`` – độ phổ biến trong phân khúc ``Mã PKKH``
        """
        merged: dict[str, tuple[float, str]] = {}
        w = self.config.weights

        for code, val in self.strategies["rule"].scores.get(customer_id, {}).items():
            if code in owned:
                continue
            merged[code] = (w.get("rule", 1.0) * val, "Luật MBA")
        for code, val in self.strategies["content"].scores.get(customer_id, {}).items():
            if code in owned:
                continue
            score, reason = merged.get(code, (0.0, ""))
            merged[code] = (
                score + w.get("content", 0.3) * val,
                f"{reason} + TF-IDF" if reason else "TF-IDF",
            )
        for code, val in self.strategies["segment"].scores.get(customer_id, {}).items():
            if code in owned:
                continue
            score, reason = merged.get(code, (0.0, ""))
            merged[code] = (
                score + w.get("segment", 1.0) * val,
                f"{reason} + Popularity PKKH" if reason else "Popularity PKKH",
            )

        ranked = sorted(merged.items(), key=lambda kv: -kv[1][0])[: self.config.top_k]
        return [
            Recommendation(
                item_code=code,
                item_name=self.item_names.get(code, code),
                score=score,
                branch="A",
                reason=reason,
            )
            for code, (score, reason) in ranked
        ]

    def _branch_b(self, customer_id: str, owned: set[str]) -> list[Recommendation]:
        """Nhánh B: popularity + lift theo phân khúc cho khách lạnh.

        Cả hai tín hiệu đều đã ở thang ``[0, 1]`` (popularity chia cho max toàn cục,
        lift chia cho max của phân khúc) nên có thể cộng trực tiếp với trọng số
        riêng cho từng tín hiệu.
        """
        w = self.config.weights
        seg = self.segments.get(customer_id, "")
        merged: dict[str, tuple[float, str]] = {}

        for code, val in self.strategies["segment"].scores.get(customer_id, {}).items():
            if code in owned:
                continue
            merged[code] = (w.get("segment", 1.0) * val, "Popularity PKKH")
        for code, val in self.strategies["segment_lift"].scores.get(customer_id, {}).items():
            if code in owned:
                continue
            score, reason = merged.get(code, (0.0, ""))
            merged[code] = (
                score + w.get("segment_lift", 0.3) * val,
                f"{reason} + Lift" if reason else "Lift PKKH",
            )

        ranked = sorted(merged.items(), key=lambda kv: -kv[1][0])[: self.config.top_k]
        return [
            Recommendation(
                item_code=code,
                item_name=self.item_names.get(code, code),
                score=score,
                branch="B",
                reason=reason,
            )
            for code, (score, reason) in ranked
        ]

    def _branch_c(self, customer_id: str, owned: set[str]) -> list[Recommendation]:
        """Nhánh C: bán chạy theo nhóm hàng liên quan (dự phòng)."""
        owned_groups = {
            self.item_groups.get(c) for c in owned if c in self.item_groups
        }
        cand: list[str] = []
        for g in list(owned_groups) + ["BOT", "SET", "TTC", "TMX", "THO"]:
            for code in self._group_best.get(g, []):
                if code not in owned and code not in cand:
                    cand.append(code)
        return [
            Recommendation(
                item_code=code,
                item_name=self.item_names.get(code, code),
                score=0.0,
                branch="C",
                reason="Best-seller theo nhóm hàng (dự phòng)",
            )
            for code in cand[: self.config.top_k]
        ]

    def recommend(self, customer_id: str) -> MultiLayerResult:
        """Sinh gợi ý cho một khách hàng theo đúng 3 nhánh."""
        owned = self.history.get(customer_id, set())
        warm = self._is_warm(customer_id)

        if warm:
            recs = self._branch_a(customer_id, owned)
            branch = "A"
        else:
            recs = self._branch_b(customer_id, owned)
            branch = "B"

        if len(recs) < self.config.top_k:
            existing = {r.item_code for r in recs}
            for r in self._branch_c(customer_id, owned):
                if len(recs) >= self.config.top_k:
                    break
                if r.item_code not in existing:
                    recs.append(r)
                    existing.add(r.item_code)

        return MultiLayerResult(
            customer_id=customer_id,
            customer_type="warm" if warm else "cold",
            segment_code=self.segments.get(customer_id, ""),
            recommendations=recs[: self.config.top_k],
            branch_used=branch,
        )

    def recommend_many(self, customer_ids: list[str]) -> dict[str, MultiLayerResult]:
        return {cid: self.recommend(cid) for cid in customer_ids}
