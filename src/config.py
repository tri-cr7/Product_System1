"""Cấu hình toàn cục của hệ thống.

Tất cả tham số có thể chỉnh sửa tập trung tại đây, tránh rải magic number trong mã nguồn.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ── Đường dẫn ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = Path("/Users/hominhtri/Downloads/data_ggsheet.xlsx")
SHEET_NAME = "data_ggsheet"
OUTPUT_DIR = ROOT / "output"
ARTIFACT_DIR = OUTPUT_DIR / "artifacts"
REPORT_DIR = OUTPUT_DIR / "report"
CHART_DIR = OUTPUT_DIR / "charts"

# ── Tên cột gốc trong file Excel (tiếng Việt) ────────────────────────────────
RAW_COLUMNS = [
    "Thời gian tạo đơn",
    "Mã đơn hàng",
    "Mã khách hàng",
    "Tên khách hàng",
    "Mã PKKH",
    "Mô tả Phân Khúc Khách hàng",
    "Mã nhóm hàng",
    "Tên nhóm hàng",
    "Mã mặt hàng",
    "Tên mặt hàng",
    "SL",
    "Đơn giá",
    "Thành tiền",
]

# Tên cột chuẩn hoá (tiếng Anh, snake_case) dùng nội bộ trong mã nguồn
CANONICAL_COLUMNS = [
    "order_time",
    "order_id",
    "customer_id",
    "customer_name",
    "segment_code",
    "segment_desc",
    "group_code",
    "group_name",
    "item_code",
    "item_name",
    "quantity",
    "unit_price",
    "amount",
]

# Cột chỉ dùng để hiển thị, KHÔNG dùng làm khóa (vì có giá trị rỗng)
DISPLAY_ONLY_COLUMNS = ["customer_name"]


@dataclass(frozen=True)
class PreprocessConfig:
    """Tầng 1 – Tiền xử lý."""

    fill_missing_name: str = "Ẩn danh"
    iqr_multiplier: float = 1.5
    #: Cột nào giữ lại outlier (đánh dấu chứ không xóa)
    outlier_keep_columns: tuple[str, ...] = ("unit_price", "amount")
    binning_columns: tuple[str, ...] = ("quantity", "unit_price")
    binning_bins: int = 5
    chi_square_alpha: float = 0.05


@dataclass(frozen=True)
class RFMConfig:
    """Tầng 2 – Đặc trưng RFM."""

    log_transform: bool = True
    scaler: str = "standard"  # "standard" (Z-score) | "minmax"
    reference_date: str | None = None  # None = dùng max(order_time) trong dữ liệu


@dataclass(frozen=True)
class ClusterConfig:
    """Tầng 2 – K-Means."""

    k_range: tuple[int, int] = (2, 12)
    n_init: int = 10
    random_state: int = 42
    selected_k: int = 3
    metric: str = "euclidean"


@dataclass(frozen=True)
class MBARulesConfig:
    """Tầng 3 – Market Basket Analysis."""

    min_support: float = 0.01
    min_support_exploratory: float = 0.005
    min_confidence: float = 0.10
    max_itemset_length: int = 3
    lift_threshold: float = 1.0
    chi_square_alpha: float = 0.05


@dataclass(frozen=True)
class RecommenderConfig:
    """Tầng 4 – Gợi ý sản phẩm."""

    ngram_range: tuple[int, int] = (1, 2)
    sublinear_tf: bool = True
    token_pattern: str = r"(?u)\b\w+\b"
    top_k: int = 5
    min_rule_confidence: float = 0.10
    #: Trọng số khi gộp nhiều chiến lược (điểm của mỗi chiến lược, đã chuẩn hoá [0,1]).
    #: Giá trị tối ưu tìm được bằng ``scripts/tune_weights.py`` trên hold-out theo thời gian
    #: (P@5 warm = 0.4085, P@5 cold = 0.4210, NDCG@5 warm = 0.6757).
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "rule": 0.5,          # luật kết hợp (confidence) — nhánh A
            "segment": 1.0,       # popularity theo PKKH — tín hiệu mạnh nhất
            "segment_lift": 0.1,  # lift theo PKKH — tín hiệu bổ trợ
            "content": 0.1,       # TF-IDF + Cosine — nhánh A
        }
    )


@dataclass(frozen=True)
class EvaluationConfig:
    """Đánh giá Tầng 4."""

    #: Ngày chốt đơn hàng để chia train / test (Slide 5 – Hold-out theo thời gian)
    split_date: str = "2022-10-01"
    k: int = 5
    n_random_baselines: int = 1


@dataclass(frozen=True)
class SystemConfig:
    """Cấu hình tổng."""

    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    rfm: RFMConfig = field(default_factory=RFMConfig)
    cluster: ClusterConfig = field(default_factory=ClusterConfig)
    mba: MBARulesConfig = field(default_factory=MBARulesConfig)
    recommender: RecommenderConfig = field(default_factory=RecommenderConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    random_state: int = 42

    def ensure_dirs(self) -> None:
        for d in (OUTPUT_DIR, ARTIFACT_DIR, REPORT_DIR, CHART_DIR):
            d.mkdir(parents=True, exist_ok=True)


CONFIG = SystemConfig()
