# HỆ THỐNG PHÂN TÍCH GIỎ HÀNG VÀ GỢI Ý SẢN PHẨM ĐA TẦNG

Hệ thống phân tích dữ liệu bán lẻ 4 tầng, triển khai đầy đủ bằng Python, kèm
REST API (FastAPI) và dashboard trực quan (Streamlit).

**Nguồn dữ liệu:** `data_ggsheet.xlsx` — 82.137 dòng giao dịch · 31.438 đơn hàng ·
9.657 khách hàng · 19 mặt hàng thuộc 5 nhóm hàng.

---

## 1. Kiến trúc 4 tầng

```
┌─ TẦNG 1: Tiền xử lý & Thống kê mô tả ────────────────────────────┐
│  Load & validate schema · fillna · drop_duplicates                  │
│  IQR outlier · Binning (equal-depth) · log + Z-score · Min-Max       │
│  Pearson correlation · Chi-square + Cramér's V                       │
└───────────────────────────┬──────────────────────────────────────────┘
                            ↓
┌─ TẦNG 2: Phân cụm hành vi ─────────────────────────────────────────┐
│  RFM (Recency/Frequency/Monetary) → log1p → StandardScaler          │
│  Lloyd K-Means · Elbow Method · Silhouette Score                    │
│  Confusion Matrix đối chiếu nhãn Mã PKKH (Hungarian matching)       │
└───────────────────────────┬──────────────────────────────────────────┘
                            ↓
┌─ TẦNG 3: Khai phá luật kết hợp ────────────────────────────────────┐
│  Apriori · Support / Confidence / Lift / Leverage / Conviction      │
│  Chi-square 2×2 cho từng luật · Targeted mining theo Mã PKKH        │
└───────────────────────────┬──────────────────────────────────────────┘
                            ↓
┌─ TẦNG 4: Gợi ý sản phẩm đa tầng ──────────────────────────────────┐
│  Nhánh A (warm)  = Luật MBA ∪ TF-IDF+Cosine ∪ Popularity PKKH      │
│  Nhánh B (cold)  = Popularity + Lift theo Mã PKKH                    │
│  Nhánh C (fallback) = Best-seller theo nhóm hàng                     │
│  Weighted Union (điểm đã chuẩn hóa [0,1]) + giải thích từng gợi ý   │
└──────────────────────────────────────────────────────────────────────┘
```

## 2. Kết quả chính (đo trên hold-out theo thời gian)

| Chỉ số | Giá trị |
| --- | --- |
| Dòng / đơn / khách | 82.137 / 31.438 / 9.657 |
| Kiểm định dữ liệu | 18/19 đạt (còn lại: `customer_name` rỗng → đã fillna) |
| Chi-square `Mã PKKH × Nhóm hàng` | χ² = 4.938,42 · p < 1e-300 · Cramér's V = 0,1226 |
| K-Means | K = 3 · Silhouette = 0,4083 · Elbow → K = 5 |
| Purity (cụm hành vi vs Mã PKKH) | 0,1635 (ngưỡng ngẫu nhiên 0,1111) |
| Luật kết hợp (support ≥ 1%) | 98 luật · Lift TB = 0,8136 |
| Toàn bộ cặp (bộ khám phá) | 171 cặp · Lift TB = 0,7926 · 8 cặp (> 1) · 163 cặp (< 1) |
| **P@5 khách ấm (đa tầng)** | **0,4085** · R@5 = 0,7332 · HR@5 = 0,9428 · NDCG@5 = 0,6757 |
| **P@5 khách lạnh (đa tầng)** | **0,4230** · R@5 = 0,5929 · HR@5 = 0,9363 · NDCG@5 = 0,5938 |
| Ngẫu nhiên (baseline) | P@5 warm = 0,2350 (+73,8%) · cold = 0,1950 (+116,9%) |

> **Phát hiện khoa học quan trọng:** 95,3% cặp sản phẩm có Lift < 1 → trong dữ liệu này
> các mặt hàng trong cùng giỏ hàng **cạnh tranh với nhau** (thay thế) chứ không bổ trợ.
> Vì vậy Apriori đơn thuần **không** sinh ra luật vận hành được, và đó chính là lý do
> tồn tại kiến trúc Tầng 4 đa tầng.

## 3. Cấu trúc mã nguồn

```
.
├── src/
│   ├── config.py                 # Cấu hình tập trung (dataclass, không magic number)
│   ├── pipeline.py               # Điều phối toàn bộ 4 tầng + lưu artifact
│   ├── data/
│   │   ├── loader.py             # Nạp Excel, đổi tên cột, ép kiểu dữ liệu
│   │   └── quality.py            # 19 kiểm tra chất lượng dữ liệu
│   ├── layers/
│   │   ├── layer1_preprocessing.py  # fillna, dedup, IQR, binning, scaling, thống kê
│   │   ├── layer1_statistics.py     # Chi-square, Cramér's V
│   │   ├── layer2_clustering.py     # RFM, K-Means, Elbow, Silhouette, Confusion Matrix
│   │   ├── layer3_mba.py            # Apriori, luật kết hợp, kiểm định chi-square
│   │   └── layer4_recommender.py    # TF-IDF, Cosine, 3 nhánh, arbitration
│   ├── evaluation/metrics.py    # Precision@k, Recall@k, Hit-Rate@k, NDCG@k
│   ├── reporting/
│   │   ├── charts.py             # 10 biểu đồ matplotlib
│   │   └── report.py             # Báo cáo Markdown tự sinh
│   └── api/main.py              # FastAPI (REST API cho lớp Operationalize)
├── dashboard/app.py              # Streamlit dashboard 6 trang
├── scripts/
│   ├── run_pipeline.py           # Chạy toàn bộ hệ thống
│   └── tune_weights.py           # Sweep trọng số gộp tín hiệu
├── tests/                        # 77 test (pytest)
├── output/
│   ├── artifacts/                # CSV/Parquet/JSON phục vụ API & dashboard
│   ├── charts/                   # 10 biểu đồ PNG
│   └── report/BAO_CAO_KET_QUA.md
└── requirements.txt
```

## 4. Cài đặt & chạy

### 4.1 Cách nhanh (khuyến nghị) — dùng `make`

```bash
cd "/Users/hominhtri/Phan tich du lieu"

make setup        # (chỉ chạy 1 lần) tạo venv + cài thư viện
make pipeline     # chạy toàn bộ hệ thống 4 tầng + biểu đồ + báo cáo
make test         # chạy 77 test
make api          # REST API  → http://localhost:8000/docs
make dashboard    # Dashboard → http://localhost:8501
make help         # xem tất cả lệnh
```

### 4.2 Cách thủ công (không dùng `make`)

```bash
cd "/Users/hominhtri/Phan tich du lieu"

# 1. Môi trường ảo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Chạy toàn bộ pipeline (4 tầng) + sinh biểu đồ + báo cáo
python scripts/run_pipeline.py

# 3. Chạy test
pytest

# 4. REST API
uvicorn src.api.main:app --reload --port 8000
#    Swagger UI: http://localhost:8000/docs

# 5. Dashboard
streamlit run dashboard/app.py
```

> **Lưu ý:** phải `activate` venv trước khi chạy `pytest` / `uvicorn` / `streamlit`.
> Nếu gặp warning về matplotlib cache hoặc joblib, hãy dùng `make` (đã cấu hình
> sẵn biến môi trường).

### 4.3 Chạy với dữ liệu khác

```bash
python scripts/run_pipeline.py --data /path/to/other.xlsx   # file Excel khác
python scripts/run_pipeline.py --no-charts --no-report      # chỉ chạy pipeline
python scripts/tune_weights.py                              # tối ưu trọng số
```

### 4.4 Kết quả sinh ra

| Đường dẫn | Nội dung |
| --- | --- |
| `output/report/BAO_CAO_KET_QUA.md` | Báo cáo Markdown đầy đủ 5 mục, có bảng + biểu đồ nhúng |
| `output/charts/` | 10 biểu đồ PNG (16:9, sẵn sàng chèn vào slide) |
| `output/artifacts/summary.json` | KPI tổng quan (dùng cho API & dashboard) |
| `output/artifacts/*.csv` | Bảng phân tích (luật, cụm, đánh giá, targeted rules) |
| `output/artifacts/*.parquet` | Dữ liệu đã xử lý (transactions, RFM) |
| `output/artifacts/item_similarity.pkl` | Ma trận Cosine similarity |

### 4.5 Với máy khác (gửi bạn bè / giáo viên)

Gửi kèm 3 thứ: `src/`, `scripts/`, `dashboard/`, `requirements.txt`.
Sau đó chạy `make setup && make pipeline` là có lại toàn bộ kết quả.

## 5. API endpoints

| Method | Path | Mô tả |
| --- | --- | --- |
| GET | `/summary` | Tóm tắt KPI toàn hệ thống |
| GET | `/customers` | Danh sách khách (lọc theo `segment`, `customer_type`) |
| GET | `/customers/{id}/recommendations` | Gợi ý đa tầng kèm nhánh & lý do |
| GET | `/items` | Danh mục mặt hàng kèm support |
| GET | `/items/{code}/similar` | Sản phẩm tương đồng (TF-IDF + Cosine) |
| GET | `/clusters` | Hồ sơ các cụm K-Means |
| GET | `/rules` | Luật kết hợp (lọc theo `min_lift`, `min_support`) |
| GET | `/evaluation` | Kết quả đánh giá Top-K (warm & cold) |
| GET | `/health` | Kiểm tra trạng thái & artifact |

## 6. Quyết định thiết kế đáng chú ý

1. **Chia hold-out theo thời gian, không chia ngẫu nhiên.** Dữ liệu có mùa vụ mạnh
   (Q4 chiếm phần lớn doanh thu) → chia ngẫu nhiên gây rò rỉ doanh thu và cho kết quả
   đánh giá lạc quan sai lệch.
2. **Chuẩn hóa điểm trước khi gộp tín hiệu.** Confidence ∈ [0,1], cosine ∈ [0,0.8],
   lift có thể > 10. Gộp trực tiếp khiến tín hiệu thang lớn "át" các tín hiệu khác và
   làm trọng số vô nghĩa.
3. **Outlier đánh dấu chứ không xóa.** Doanh thu cao là khách giá trị cao, xóa đi sẽ
   làm sai lệch phân tích phân khúc.
4. **`Mã PKKH` là thuộc tính tĩnh** → dùng được cho khách lạnh, giải quyết cold-start
   có nguyên tắc thay vì chỉ dùng popular toàn cục.
5. **K chọn theo nghiệp vụ, không theo Silhouette tối đa.** Silhouette đạt đỉnh ở K=2
   (0,4825) nhưng 3 cụm (VIP / Trung thành / Cần chăm sóc) mới dùng được vận hành →
   ghi rõ trong báo cáo để bảo vệ.
6. **Bộ luật khám phá tách riêng bộ luật vận hành.** Lọc support trước sẽ che mất các
   luật Lift > 1 có support thấp, dẫn tới kết luận sai về khả năng của Apriori.

## 7. Tương quan với giáo trình

| Thuật toán | Slide | Nơi triển khai |
| --- | --- | --- |
| Data cleaning (fillna, drop_duplicates) | 2.2 | `src/data/loader.py`, `src/layers/layer1_preprocessing.py` |
| Kiểm định Chi-square | 1.1 | `src/layers/layer1_statistics.py` |
| Pearson correlation | 1.1 | `layer1_preprocessing.pearson_correlation` |
| Binning / Min-Max / Z-score | 1.1 | `layer1_preprocessing` |
| Phân tích thống kê mô tả | 4 | `layer1_preprocessing.describe_numeric` |
| IQR outlier | 4 | `layer1_preprocessing.detect_outliers_iqr` |
| K-Means | 5.3 | `layer2_clustering.run_kmeans` |
| Confusion Matrix + P/R/F1 | 5 | `layer2_clustering.evaluate_against_segments` |
| TF-IDF / Cosine Similarity | 5.2 (mở rộng) | `layer4_recommender.build_item_index` |
| Precision@k / Recall@k / NDCG@k | 5 (mở rộng) | `src/evaluation/metrics.py` |
| **Mở rộng:** RFM, Apriori, Elbow, Silhouette, Leverage/Conviction, Targeted mining | — | các module Tầng 2–3 |
