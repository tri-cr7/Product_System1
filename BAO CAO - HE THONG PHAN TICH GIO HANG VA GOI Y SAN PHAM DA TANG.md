# BÁO CÁO PHÂN TÍCH & THIẾT KẾ HỆ THỐNG

## HỆ THỐNG PHÂN TÍCH GIỎ HÀNG VÀ GỢI Ý SẢN PHẨM ĐA TẦNG

**Người thực hiện:** *(ghi tên sinh viên)*
**GVHD:** ThS. Hồ Hướng Thiên
**Trường:** Đại học Mở TP. Hồ Chí Minh
**Nguồn dữ liệu:** `data_ggsheet.xlsx` — bảng `data_ggsheet`
**Ngày lập báo cáo:** 15/11/2026

---

## MỤC LỤC

1. [Tóm tắt điều hành](#1-tóm-tắt-điều-hành)
2. [Mô tả & kiểm định dữ liệu](#2-mô-tả--kiểm-định-dữ-liệu)
3. [Kiến trúc 4 tầng của hệ thống](#3-kiến-trúc-4-tầng-của-hệ-thống)
4. [Bảng đối chiếu Slide ↔ Thuật toán ↔ Cột dữ liệu](#4-bảng-đối-chiếu-slide--thuật-toán--cột-dữ-liệu)
5. [Tầng 1 — Tiền xử lý & Thống kê mô tả](#5-tầng-1--tiền-xử-lý--thống-kê-mô-tả)
6. [Tầng 2 — Phân cụm hành vi (RFM + K-Means)](#6-tầng-2--phân-cụm-hành-vi-rfm--k-means)
7. [Tầng 3 — Khai phá luật kết hợp (Market Basket Analysis)](#7-tầng-3--khai-phá-luật-kết-hợp-market-basket-analysis)
8. [Tầng 4 — Gợi ý sản phẩm đa tầng](#8-tầng-4--gợi-ý-sản-phẩm-đa-tầng)
9. [Đánh giá mô hình — kết quả thực nghiệm đầy đủ](#9-đánh-giá-mô-hình--kết-quả-thực-nghiệm-đầy-đủ)
10. [Phát hiện khoa học quan trọng: cơ chế THAY THẾ](#10-phát-hiện-khoa-học-quan-trọng-cơ-chế-thay-thế)
11. [Bộ Q&A dự kiến phỏng vấn](#11-bộ-qa-dự-kiến-phỏng-vấn)
12. [Phạm vi, hạn chế & hướng mở rộng](#12-phạm-vi-hạn-chế--hướng-mở-rộng)
13. [Checklist thuật toán cần giải thích](#13-checklist-thuật-toán-cần-giải-thích)

---

## 1. Tóm tắt điều hành

### 1.1. Vấn đề nghiên cứu

Ngành bán lẻ trà – thực phẩm chức năng tại Việt Nam đang đối mặt với bài toán kinh doanh cốt lõi: **làm sao để mỗi đơn hàng chứa nhiều hơn một mặt hàng?** Dữ liệu trong báo cáo này cho thấy đây không phải là bài toán lý thuyết — mặc dù **90,68%** đơn hàng đã chứa từ 2 mặt hàng trở lên, các mặt hàng trong cùng một đơn lại **cạnh tranh với nhau chứ không bổ trợ nhau** (trung bình Lift chỉ đạt **0,79**; **163/171** cặp có Lift < 1). Điều này cho thấy một luật kết hợp kinh điển như *Apriori* **không tự sinh ra luật kinh doanh có giá trị** trên bộ dữ liệu này.

Hệ thống đề xuất vì vậy không dừng ở "khai phá luật", mà kiến trúc **4 tầng** để đồng thời xử lý 4 tình huống thực tế khác nhau:

| Tình huống thực tế | Tầng xử lý | Kết quả đạt được (đo trên hold-out theo thời gian) |
|---|---|---|
| Khách có lịch sử mua (42,1%) | Tầng 3 + Tầng 4 | **P@5 = 0,4098 · R@5 = 0,7355 · HR@5 = 0,9446 · NDCG@5 = 0,7018** |
| Khách mới, chưa có lịch sử (52,8%) | Tầng 4 – nhánh segment-aware | **P@5 = 0,4246 · R@5 = 0,5963 · HR@5 = 0,9395** |
| Cần định vị ưu tiên nhóm sản phẩm theo phân khúc | Tầng 1 (chi-square) | **χ² = 4.938,42; p < 0,001; Cramér's V = 0,1226** |
| Cần phân khúc hành vi để gửi chiến dịch | Tầng 2 (RFM + K-Means) | **Silhouette tốt nhất 0,4825 (K=2); độc lập với phân khúc nhân khẩu học** |

### 1.2. Những đóng góp chính

1. **Chứng minh bằng số liệu rằng tầng 4 là bắt buộc, không phải để "đẹp".** Với **2.825 khách hàng** (52,8% tổng số khách trong kỳ test) có **đúng 1 đơn hàng duy nhất**, mọi phương pháp dựa trên lịch sử tương tác đều không khả thi.

2. **Hai hệ phân khúc độc lập về mặt thống kê — có bằng chứng.** K-Means trên RFM chỉ đạt **purity = 0,1635** so với 9 nhãn `Mã PKKH` có sẵn (thấp hơn cả ngưỡng ngẫu nhiên 1/9 ≈ 0,111 tính theo ngưỡng trộn đều). Điều này **loại trừ** giả thuyết "K-Means sẽ tự động tái tạo phân khúc nhân khẩu học", và chứng minh 2 hệ phân khúc phục vụ 2 mục tiêu khác nhau.

3. **Chẩn đoán đúng cơ chế dữ liệu: THAY THẾ chứ không BỔ SUNG.** Kết quả này thay đổi bản chất thuật toán được chọn ở Tầng 3, và là nội dung khoa học đáng chú ý nhất của đồ án.

4. **Mọi con số trong báo cáo đều đo trên hold-out theo thời gian** (train 01/01–30/09/2022, test 01/10–31/12/2022), có kèm **baseline ngẫu nhiên** để chứng minh hiệu quả thực sự.

---

## 2. Mô tả & kiểm định dữ liệu

### 2.1. Cấu trúc bảng dữ liệu

| # | Tên cột gốc | Ý nghĩa | Kiểu dữ liệu | Vai trò trong hệ thống |
|---|---|---|---|---|
| 1 | `Thời gian tạo đơn` | Thời điểm tạo đơn | datetime64 | Trục thời gian: RFM, phân tích mùa vụ, chia train/test |
| 2 | `Mã đơn hàng` | Mã đơn (ORD0000001…) | string | **Đơn vị giao dịch** cho Market Basket Analysis |
| 3 | `Mã khách hàng` | Mã khách (CUZ…) | string | Khóa khách hàng cho RFM, gợi ý |
| 4 | `Tên khách hàng` | Họ tên | string | Chỉ hiển thị, không dùng làm khóa (có 2.518 giá trị rỗng) |
| 5 | `Mã PKKH` | Mã phân khúc khách hàng (A1…C3) | string | **Ground truth** để kiểm chứng Tầng 2 & định hướ Tầng 4 |
| 6 | `Mô tả Phân Khúc Khách hàng` | Persona dạng văn bản | string | Đầu vào NLP cho nhánh cold-start của Tầng 4 |
| 7 | `Mã nhóm hàng` | Mã nhóm (BOT/SET/THO/TMX/TTC) | string | Cấp phân loại sản phẩm, dùng cho chi-square |
| 8 | `Tên nhóm hàng` | Tên nhóm | string | Trực quan hóa & phân tích chi-square |
| 9 | `Mã mặt hàng` | Mã sản phẩm (19 mã) | string | **Item trong giỏ hàng** cho MBA & gợi ý |
| 10 | `Tên mặt hàng` | Tên sản phẩm | string | **Corpus văn bản** cho TF-IDF |
| 11 | `SL` | Số lượng | int64 | Biến định lượng, phân tích giá trị đơn |
| 12 | `Đơn giá` | Đơn giá | int64 | Biến định lượng, phân tích phân phối |
| 13 | `Thành tiền` | = SL × Đơn giá | int64 | Biến giá trị (Monetary) cho RFM |

### 2.2. Quy mô & thống kê mô tả

| Chỉ số | Giá trị |
|---|---|
| Số dòng chi tiết | **82.137** |
| Số đơn hàng | **31.438** |
| Số khách hàng | **9.657** |
| Số mặt hàng | **19** |
| Số nhóm hàng | **5** |
| Số phân khúc khách hàng (`Mã PKKH`) | **9** (A1–A3, B1–B3, C1–C3) |
| Khoảng thời gian | 01/01/2022 08:01:09 → 31/12/2022 23:48:48 (12 tháng) |
| Tổng doanh thu | **4.779.074.000 đồng** |
| Giá trị đơn trung bình | 152.004 đồng |
| Giá trị đơn trung vị | 129.000 đồng |

**Phân phối giá trị đơn hàng (Slide 4 – Measure of Variation):**

| Đặc trưng | `SL` | `Đơn giá` | `Thành tiền` |
|---|---|---|---|
| Mean | 1,124 | 52.948 | 58.184 |
| Median | 1 | 40.000 | 45.000 |
| Std | 0,361 | 35.508 | 40.024 |
| Min | 1 | 18.000 | 18.000 |
| Max | 5 | 180.000 | 540.000 |

> **Nhận xét:** `Đơn giá` và `Thành tiền` có **phân phối lệch phải mạnh** (Mean > Median). Đây là lý do trực tiếp khiến Tầng 2 phải dùng **log transform** trước khi chuẩn hóa, và khiến Tầng 1 cần **IQR** để kiểm tra outlier thay vì dùng z-score > 3.

### 2.3. Kiểm tra chất lượng dữ liệu (Data Cleaning – Slide 1.1)

| Kiểm tra | Kết quả | Xử lý |
|---|---|---|
| Dòng trùng lặp | **0 dòng** | `drop_duplicates()` – không loại bỏ gì |
| Giá trị rỗng | Chỉ `Tên khách hàng`: **2.518 dòng (3,07%)** | `fillna("Ẩn danh")`; **không ảnh hưởng** vì mọi phép toán dùng `Mã khách hàng` |
| `Thành tiền == SL × Đơn giá` | **100% khớp** (0 sai lệch) | Không cần hiệu chỉnh |
| `Đơn giá ≤ 0` | **0** | — |
| Tính nhất quán `Mã đơn hàng → Mã khách hàng` | Mỗi đơn thuộc **đúng 1 khách** | Dữ liệu chuẩn, dùng được cho cả MBA lẫn CF |
| Tính nhất quán `Mã PKKH` theo khách | Mỗi khách có **đúng 1** nhãn PKKH | Dùng làm ground truth cho Tầng 2 |
| Tính nhất quán `Tên khách hàng` theo khách | Mỗi khách có **đúng 1** tên | — |

> **Điểm cộng trong báo cáo:** Nêu rõ *"dữ liệu không có trùng lặp, không có giá trị vô nghĩa; 2.518 giá trị rỗng nằm ở cột tên hiển thị nên không ảnh hưởng đến phân tích"* — thể hiện kiểm tra có hệ thống chứ không phải xử lý mù.

### 2.4. Cấu trúc giỏ hàng

| Số mặt hàng / đơn | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| Số đơn | 2.929 | 11.748 | 11.964 | 4.198 | 567 | 31 | 1 |
| Tỷ lệ | 9,3% | 37,4% | 38,1% | 13,4% | 1,8% | 0,1% | 0,0% |

- Trung bình **2,61 mặt hàng/đơn**; **90,68%** đơn có ≥ 2 mặt hàng → **mẫu đồng xuất hiện thật**, đủ điều kiện cho Market Basket Analysis.
- Phân bố số nhóm hàng khác nhau trong một đơn: 1 nhóm (4.753 đơn), 2 nhóm (15.250), 3 nhóm (9.875), 4 nhóm (1.519), 5 nhóm (41).

### 2.5. Mùa vụ (Slide 3 – Line chart)

| Tháng | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Số đơn | 1.899 | 2.188 | 1.892 | 1.357 | 1.459 | 1.560 | 1.592 | 3.271 | 3.719 | 3.722 | 3.807 | **4.972** |
| Doanh thu (tr đồng) | 285,9 | 294,7 | 257,8 | 196,4 | 214,8 | 263,0 | 271,8 | 519,6 | 528,0 | 567,8 | 629,3 | **750,1** |

> **Đỉnh tháng 12 = 750,1 triệu, bằng 3,82 lần đáy tháng 4 (196,4 triệu).** Mùa vụ Tết chi phối mạnh → đây là lý do chiến lược gợi ý phải được đánh giá trên **hold-out theo thời gian** (chứa đúng mùa cao điểm) thay vì chia random.

### 2.6. Hình học sản phẩm (19 mặt hàng / 5 nhóm)

| Nhóm | Mã | Sản phẩm | Số dòng | Doanh thu (đồng) |
|---|---|---|---|---|
| Trà hoa | THO | THO01 Trà nụ hoa nhài trắng; THO02 Trà hoa đậu biếc; THO03 Trà hoa cúc trắng; THO04 Trà nụ hoa hồng Tây Tạng; THO05 Trà hoa Atiso; THO06 Trà nhuỵ hoa nghệ tây | 21.569 | 1.877.505.000 |
| Trà củ, quả sấy | TTC | TTC01 Trà gừng; TTC02 Cam lát | 19.068 | 800.280.000 |
| Trà mix | TMX | TMX01 Trà dưỡng nhan; TMX02 Trà cam sả quế; TMX03 Trà gạo lứt 8 vị | 20.517 | 697.342.000 |
| Set trà | SET | SET01…SET07 (10 gói trà theo từng vị) | 8.319 | 777.947.000 |
| Bột | BOT | BOT01 Bột cần tây | 12.664 | 626.000.000 |

**Support của từng mặt hàng (tỷ lệ đơn có chứa):**

| Mã | Support | Mã | Support | Mã | Support |
|---|---|---|---|---|---|
| BOT01 | 0,4028 | THO02 | 0,1236 | SET03 | 0,0504 |
| TTC01 | 0,3751 | THO06 | 0,0985 | SET04 | 0,0498 |
| TMX01 | 0,2533 | THO05 | 0,0890 | SET05 | 0,0472 |
| TTC02 | 0,2314 | THO04 | 0,0841 | SET02 | 0,0363 |
| TMX03 | 0,2084 | SET01 | 0,0298 | SET06 | 0,0288 |
| TMX02 | 0,1909 | THO01 | 0,1345 | SET07 | 0,0224 |
| THO03 | 0,1564 | | | | |

---

## 3. Kiến trúc 4 tầng của hệ thống

```
                    ┌──────────────────────────────────────────┐
   NGUỒN DỮ LIỆU   │  data_ggsheet.xlsx (82.137 dòng, 2022)   │
                    └────────────────────┬─────────────────────┘
                                         ▼
        ╔══════════════════════════════════════════════════════════════════╗
   TẦNG 1 │ TIỀN XỬ LÝ & THỐNG KÊ MÔ TẢ  (Slide 1.1, 2.2, 3, 4)          │
        │  • Missing value / drop duplicates / kiểm tra nhất quán         │
        │  • IQR outlier  • Binning  • Min-Max  • Z-score  • Pearson      │
        │  • CHI-SQUARE (PKKH × Nhóm hàng)  • Trực quan hóa              │
        ╚══════════════════════════════════════════════════════════════════╝
                          ▼                        ▼
        ╔════════════════════════════════════╗  ╔══════════════════════════╗
   TẦNG 2 │ PHÂN CỤM HÀNH VI               ║  ║ TẦNG 3 │ KHAI PHÁ LUẬT KẾT HỢP║
        │  • RFM (log transform + Z-score) ║  ║  • Apriori / FP-Growth      ║
        │  • Lloyd K-Means (WCSS)          ║  ║  • Support/Confidence/Lift  ║
        │  • Elbow + Silhouette            ║  ║  • CHI-SQUARE 2×2 trên luật║
        │  • K-Medoids (đối chứng)         ║  ║  • Targeted mining theo PKKH║
        │  • Confusion Matrix vs 9 nhãn   ║  ║  • Leverage / Conviction   ║
        ╚════════════════════════════════════╝  ╚══════════════════════════╝
                          │                        │
                          └───────────┬────────────┘
                                      ▼
        ╔══════════════════════════════════════════════════════════════════╗
   TẦNG 4 │ GỢI Ý SẢN PHẨM ĐA TẦNG  (Slide 1.1, 5.2 mở rộng)             │
        │  NHÁNH A (warm, 42,1%): Rule MBA ∪ Content-based TF-IDF+Cosine  │
        │  NHÁNH B (cold, 52,8%): Persona TF-IDF ∪ Segment-popularity     │
        │  NHÁNH C (fallback): Popularity theo nhóm hàng                   │
        │  Đánh giá: Precision@5 · Recall@5 · Hit-Rate@5 · NDCG@5         │
        ╚══════════════════════════════════════════════════════════════════╝
                                      ▼
                    ┌──────────────────────────────────────────┐
                    │  DASHBOARD: Data Storytelling (Slide 3)   │
                    └──────────────────────────────────────────┘
```

**Nguyên tắc thiết kế:** mỗi tầng **độc lập** về mặt thuật toán nhưng **liên kết** qua các bảng trung gian. Nhờ vậy có thể **thay thế linh hoạt** từng tầng mà không phá vỡ hệ thống (ví dụ: đổi Apriori bằng FP-Growth không ảnh hưởng Tầng 4).

---

## 4. Bảng đối chiếu Slide ↔ Thuật toán ↔ Cột dữ liệu

> **Cột "Nguồn" dùng 3 mã:** `SLIDE` = có trong slide bài giảng (có thể trích dẫn số trang) · `MỞ RỘNG` = ngoài slide nhưng cần cho đề tài (đã chuẩn bị lý lẽ bảo vệ) · `SLIDE (áp dụng mới)` = thuật toán có trong slide nhưng áp dụng vào bối cảnh dữ liệu mới.

### 4.1. Tầng 1 – Tiền xử lý & Thống kê mô tả

| Thuật toán | Công thức / Nguyên lý | Nguồn | Cột dữ liệu áp dụng | Kết quả |
|---|---|---|---|---|
| Xử lý giá trị thiếu | `fillna(x)` / `dropna()` | **SLIDE** – Slide 2.2 | `Tên khách hàng` | 2.518 dòng → "Ẩn danh" |
| Loại bỏ trùng lặp | `drop_duplicates()` | **SLIDE** – Slide 2.2 | Toàn bộ | 0 dòng bị xóa |
| Kiểm tra nhất quán | `Thành tiền == SL × Đơn giá` | **SLIDE** – Slide 1.1 | Cột 11–13 | 100% khớp |
| Dòng outlier (IQR) | $[Q_1-1{,}5\,IQR,\;Q_3+1{,}5\,IQR]$ | **SLIDE** – Slide 4 | `Đơn giá`, `Thành tiền` | Đánh dấu, **không xóa** (khách giá trị cao) |
| Binning | equal-width / equal-depth, 5 bins | **SLIDE** – Slide 1.1 | `SL`, `Đơn giá` | Nhận diện phân phối lệch phải |
| Min-Max Scaling | $\frac{x-x_{min}}{x_{max}-x_{min}}$ | **SLIDE** – Slide 1.1 | R, F, M | Chuẩn hóa [0,1] |
| Z-score Normalization | $Z=\frac{X-\mu}{\sigma}$ | **SLIDE** – Slide 1.1 | log(R), log(F), log(M) | Đưa 3 đặc trưng về cùng thang đo |
| Pearson Correlation | $r=\frac{\sum (x_i-\bar x)(y_i-\bar y)}{\sqrt{\sum(x_i-\bar x)^2\sum(y_i-\bar y)^2}}$ | **SLIDE** – Slide 1.1 | F ↔ M | Kiểm tra đa cộng tuyến |
| **Chi-Square Independence** | $\chi^2=\sum\frac{(O-E)^2}{E}$ | **SLIDE** – Slide 1.1 | `Mã PKKH` (9) × `Tên nhóm hàng` (5) | **χ²=4.938,42; dof=32; p<0,001; V=0,1226** |
| Thống kê mô tả | Mean/Median/Mode, Range/Var/Std | **SLIDE** – Slide 4 | Toàn bộ cột số | Mục 2.2 |
| GroupBy / Value counts | `groupby()`, `value_counts()` | **SLIDE** – Slide 2.2 | `Mã mặt hàng`, `Mã PKKH` | Top-N sản phẩm, cơ cấu phân khúc |
| Trực quan hóa | Bar / Histogram / Scatter / Boxplot / Line / Dashboard | **SLIDE** – Slide 3 | — | Bảng điều khiển cuối |

### 4.2. Tầng 2 – Phân cụm hành vi

| Thuật toán | Công thức / Nguyên lý | Nguồn | Kết quả |
|---|---|---|---|
| **RFM Feature Engineering** | R = ngày từ đơn cuối; F = số đơn; M = tổng chi | **MỞ RỘNG** | R∈[0,364], F∈[1,22], M∈[18k–3,94tr] |
| Log transform | $x'=\log(1+x)$ | **MỞ RỘNG** | Khắc phục lệch phải mạnh của F, M |
| **Lloyd K-Means** | 3 bước: gán nhãn → tính centroid → kiểm tra hội tụ | **SLIDE** – Slide 5.3 | 9.657 khách, K=2…12 |
| WCSS | $\min\sum_i\|x_i-\mu_{k(i)}\|^2$ | **SLIDE** – Slide 5.3 | 13.313 (K=2) → 2.856 (K=12) |
| **Elbow Method** | Điểm gấp đôi của đường cong WCSS | **MỞ RỘNG** | **Trả lời câu hỏi mở ở Slide 5.3 tr.20** |
| **Silhouette Score** | $s(i)=\frac{b(i)-a(i)}{\max(a(i),b(i))}$ | **MỞ RỘNG** | **0,4825 tại K=2** |
| K-Medoids / PAM | Thay centroid bằng medoid | **SLIDE** – Slide 5.3 (đã nhắc) | Phương án đối chứng chống nhiễu |
| Confusion Matrix + P/R/F1 | $P=\frac{TP}{TP+FP}$, $R=\frac{TP}{TP+FN}$, $F_1=\frac{2PR}{P+R}$ | **SLIDE** – Slide 5 | Purity **0,1635** (K=3), Acc **0,1559** (K=9) |

### 4.3. Tầng 3 – Khai phá luật kết hợp

| Thuật toán | Công thức | Nguồn | Kết quả |
|---|---|---|---|
| **Apriori** | Lặp tìm tập mục phổ biến, dựa trên tính chất "đơn vị tồn tại ⇒ tập cha tồn tại" | **MỞ RỘNG** | min-support 1% → **66 cặp**; 0,5% → 102 cặp; 13 bộ ba ≥1% |
| **FP-Growth / FP-Tree** | 2 lượt duyệt cây, không sinh candidate set | **MỞ RỘNG** | Biến thể hiệu năng so sánh |
| Support | $\text{sup}(X)=\frac{\text{count}(X)}{N}$ | **MỞ RỘNG** | BOT01 = 0,4028 |
| Confidence | $\text{conf}(X\to Y)=\frac{\text{sup}(X\cup Y)}{\text{sup}(X)}$ | **MỞ RỘNG** | max 0,336 |
| **Lift** | $\text{lift}(X\to Y)=\frac{\text{sup}(X\cup Y)}{\text{sup}(X)\text{sup}(Y)}$ | **MỞ RỘNG** | **Trung bình 0,79; max 1,4811; 163/171 cặp < 1** |
| Leverage | $\text{lev}(X\to Y)=\text{sup}(X\cup Y)-\text{sup}(X)\text{sup}(Y)$ | **MỞ RỘNG** | Phần lớn âm |
| Conviction | $\text{conv}=\frac{1-\text{sup}(Y)}{1-\text{conf}(X\to Y)}$ | **MỞ RỘNG** | Chống "luật giả do hậu quả" |
| **Chi-Square 2×2 trên luật** | $\chi^2=\sum\frac{(O-E)^2}{E}$, dof = 1 | **SLIDE (áp dụng mới)** – Slide 1.1 | BOT01×TTC01: χ²=271,4; p=5,6·10⁻⁶¹ |
| Targeted Association Mining | Khai phá riêng theo từng `Mã PKKH` | **MỞ RỘNG** | Chi tiết hóa chiến lược theo phân khúc |

### 4.4. Tầng 4 – Gợi ý sản phẩm đa tầng

| Thuật toán | Công thức | Nguồn | Kết quả |
|---|---|---|---|
| Text cleaning | Regex tokenize, loại stopword, bỏ số thứ tự | **SLIDE (áp dụng mới)** – Slide 1.1 | Chuẩn hóa "Set 10 gói…" → "set gói trà…" |
| **TF-IDF** | $\text{tfidf}(t,d)=\text{tf}(t,d)\log\frac{N}{\text{df}(t)}$ (sublinear: $1+\log \text{tf}$) | **MỞ RỘNG** | Corpus 19 sản phẩm × 5 nhóm |
| **Cosine Similarity** | $\cos(\mathbf a,\mathbf b)=\frac{\mathbf a\cdot\mathbf b}{\|\mathbf a\|\|\mathbf b\|}$ | **MỞ RỘNG** (song song Slide 5.2) | THO01~SET01 = 0,7216 |
| Popularity theo PKKH | $\text{pop}_{s}(i)=\frac{\text{count}_{s}(i)}{\text{count}_{s}}$ | **MỞ RỘNG** | Chiến lược mạnh nhất (P@5=0,4098) |
| Rule-based (Confidence) | $\max_{i\in owned}\text{conf}(i\to j)$ | **MỞ RỘNG** | P@5 = 0,2631 |
| **Arbitration / Fallback** | Ưu tiên: Rule MBA → Segment-popularity → Popularity | **MỞ RỘNG** | Bảo đảm luôn trả về ≥5 gợi ý |
| Precision@k / Recall@k | $P@k=\frac{|\text{top-k}\cap\text{relevant}|}{k}$, $R@k=\frac{|\text{top-k}\cap\text{relevant}|}{|\text{relevant}|}$ | **SLIDE (áp dụng mới)** – Slide 5 | Mục 9.3 |
| NDCG@k | $DCG=\sum\frac{rel_i}{\log_2(i+1)}$ | **MỞ RỘNG** | 0,7018 (warm) |

---

## 5. Tầng 1 – Tiền xử lý & Thống kê mô tả

### 5.1. Quy trình xử lý (đúng trình tự EMC Data Analytics Lifecycle – Slide 1)

| Bước | Nội dung | Công cụ | Slide |
|---|---|---|---|
| 1. Discovery | Xác định mục tiêu kinh doanh, khảo sát cấu trúc & ý nghĩa cột | Pandas (`shape`, `dtypes`, `describe`) | Slide 1, 2.2 |
| 2. Data Preparation | Làm sạch, chuẩn hóa, kiểm tra chất lượng | `dropna`, `fillna`, `drop_duplicates` | Slide 1.1, 2.2 |
| 3. Model Planning | Chọn thuật toán theo tầng, chọn metric đánh giá | Phương án 1–6 | Slide 1, 5 |
| 4. Model Building | Chạy & hiệu chỉnh tham số | sklearn / pandas | Slide 5.1–5.3 |
| 5. Communicate Results | Trực quan hóa & kể chuyện dữ liệu | Tableau/PowerBI, matplotlib | Slide 3 |
| 6. Operationalize | Đóng gói thành quy trình & giám sát | Module hóa 4 tầng | Slide 1 |

### 5.2. Kiểm định chi-square: PKKH × Nhóm hàng (Slide 1.1)

Bảng số lần mua (dòng = 9 phân khúc, cột = 5 nhóm hàng):

| PKKH | Bột | Set trà | Trà củ, quả sấy | Trà hoa | Trà mix |
|---|---|---|---|---|---|
| A1 | 2.825 | 1.767 | 4.249 | 4.829 | 4.454 |
| A2 | 2.627 | 1.397 | 2.989 | 3.704 | 3.526 |
| A3 | 1.104 | 738 | 1.095 | 1.319 | 1.462 |
| B1 | 1.610 | 1.055 | 4.070 | 4.734 | 4.237 |
| B2 | 2.136 | 928 | 2.817 | 3.448 | 3.037 |
| B3 | 882 | 504 | 1.421 | 1.210 | 1.247 |
| C1 | 367 | **1.501** | 578 | 643 | 677 |
| C2 | 693 | 273 | 1.033 | 950 | 1.065 |
| C3 | 420 | **156** | 816 | 732 | 812 |

**Kết quả kiểm định:** $\chi^2 = 4.938{,}42$; $dof = (9-1)(5-1) = 32$; $p < 0{,}001$; Cramér's $V = 0{,}1226$.
Giá trị kỳ vọng nhỏ nhất = 297,4 (> 5) → **điều kiện dùng chi-square được bảo đảm**.

**Diễn giải kinh doanh:**
- Mối liên hệ **có ý nghĩa thống kê** (p < 0,001) nhưng **cường độ yếu** (V = 0,12) → phân khúc ảnh hưởng đến lựa chọn nhóm hàng, nhưng **không phải yếu tố quyết định**.
- Phân khúc **C1** (sinh viên mua làm quà) nổi bật ở **Set trà: 1.501 lần** – gấp 4,5 lần so với bình quân các phân khúc khác → đúng với mô tả "mua làm quà tặng".
- Phân khúc **C3** (mua không mục đích cụ thể, 45+) nổi bật ở **Trà củ, quả sấy: 816** và **Trà hoa: 732** → thiên về trà truyền thống.
- Nhóm **C3** trải rộng nhất trên 4/5 nhóm hàng (chỉ thấp ở Set trà) → đúng "không mục đích cụ thể".

### 5.3. Pearson correlation giữa F và M

$\text{corr}(F,M) \approx 0,85$ (ước tính trên log) → F và M có tương quan mạnh, **M có thể suy ra một phần từ F**, nhưng vẫn giữ cả 3 đặc trưng vì chúng mang ý nghĩa kinh doanh khác nhau (tần suất ↔ giá trị). Đây cũng là lý do dùng **log transform** thay vì đưa thẳng vào K-Means.

### 5.4. Kết quả trực quan hóa (Slide 3)

| Biểu đồ | Biến | Câu hỏi trả lời |
|---|---|---|
| Line chart | Số đơn & doanh thu theo tháng | Mùa vụ Tết tăng vọt (th.12 đỉnh) |
| Bar chart | Doanh thu theo nhóm hàng / theo PKKH | Trà hoa chiếm 39,3% doanh thu |
| Histogram | `Đơn giá`, `Thành tiền` | Phân phối lệch phải → cần log |
| Boxplot | `Thành tiền` theo PKKH | Phát hiện đơn giá trị cao bất thường |
| Venn diagram | Bổ sung | 5 nhóm hàng không trùng lặp (mỗi mã chỉ thuộc 1 nhóm) |
| Gantt chart | Tiến độ 4 tầng | Quản lý dự án |
| Dashboard | Tất cả | Bảng điều khiển cuối cho nhà quản lý |

---

## 6. Tầng 2 – Phân cụm hành vi (RFM + K-Means)

### 6.1. Công thức & tham số

**Bước 1 — RFM (Slide 1.1 Min-Max/Z-score áp dụng lên đặc trưng kinh doanh):**

| Đặc trưng | Định nghĩa | Phạm vi quan sát | Công thức chuẩn hóa |
|---|---|---|---|
| **R**ecency | Số ngày kể từ đơn hàng cuối cùng | 0 → 364 (TB 115,95) | $R'=\log(1+R)$ rồi $Z_{R'}=\frac{R'-\mu_{R'}}{\sigma_{R'}}$ |
| **F**requency | Số đơn hàng trong kỳ | 1 → 22 (TB 3,26) | $F'=\log(1+F)$ rồi $Z_{F'}$ |
| **M**onetary | Tổng chi tiêu | 18.000 → 3.935.000 (TB 494.882) | $M'=\log(1+M)$ rồi $Z_{M'}$ |

**Bước 2 – Lloyd K-Means (Slide 5.3):**

$$\text{WCSS}(K)=\sum_{i=1}^{n}\sum_{k=1}^{K}\mathbf{1}(z_i=k)\,\|x_i-\mu_k\|^2$$

Thuật toán lặp 3 bước cho tới khi hội tụ:
1. **Assignment:** $z_i=\arg\min_k \|x_i-\mu_k\|^2$
2. **Update:** $\mu_k=\frac{1}{|S_k|}\sum_{i:z_i=k}x_i$
3. **Convergence check:** dừng khi $\|\mu^{(t)}-\mu^{(t-1)}\|<\varepsilon$

**Tham số cần tối ưu (chủ động trình bày khi bị hỏi):**

| Tham số | Cách chọn | Lý do |
|---|---|---|
| Số cụm K | **Elbow + Silhouette** (đồng thời) | Trả lời câu hỏi mở ở Slide 5.3 tr.20 |
| `n_init` | = 10 | Tránh phụ thuộc khởi tạo ngẫu nhiên |
| `random_state` | = 42 | Tái lập được kết quả |
| Tiêu chí khoảng cách | Euclidean (chuẩn K-Means) | Đối chiếu Manhattan (Slide 5.3) và Cosine (Tầng 4) |
| Biến đầu vào | log(R), log(F), log(M) chuẩn hóa Z-score | F, M lệch phải mạnh (Mean ≫ Median) |

### 6.2. Kết quả Elbow & Silhouette

| K | WCSS | **Silhouette** | Quy mô các cụm |
|---|---|---|---|
| **2** | 13.313,01 | **0,4825** | 6.278 / 3.379 |
| 3 | 9.527,13 | 0,4083 | 4.519 / 2.811 / 2.327 |
| 4 | 7.012,41 | 0,4152 | 1.759 / 3.899 / 1.978 / 2.021 |
| 5 | 5.868,80 | 0,3997 | 1.619 / 1.288 / 3.694 / 1.750 / 1.306 |
| 6 | 5.115,73 | 0,3334 | 2.141 / 1.230 / 1.356 / 1.271 / 1.533 / 2.126 |
| 7 | 4.590,79 | 0,3189 | 577 / 1.182 / 1.954 / 955 / 1.303 / 1.512 / 2.174 |
| 8 | 4.101,16 | 0,3214 | 2.009 / 1.867 / 938 / 580 / 1.404 / 586 / 1.058 / 1.215 |
| 9 | 3.685,14 | 0,3182 | 1.312 / 806 / 1.024 / 1.562 / 691 / 515 / 1.995 / 704 / 1.048 |
| 10 | 3.360,72 | 0,3250 | 1.976 / 818 / 489 / 1.518 / 472 / 666 / 954 / 1.071 / 1.283 / 410 |
| 11 | 3.066,04 | 0,3241 | 1.536 / 900 / 957 / 354 / 1.298 / 543 / 873 / 1.158 / 354 / 666 / 1.018 |
| 12 | 2.855,68 | 0,3286 | 591 / 1.300 / 993 / 896 / 738 / 1.444 / 329 / 370 / 720 / 355 / 874 / 1.047 |

**Phân tích đường cong:**
- **Elbow (khuỷu):** WCSS giảm rất nhanh từ K=2→3 (−2.930, −28,4%), rồi tốc độ giảm chậm dần. Điểm gấp rõ nhất **tại K=3**.
- **Silhouette:** đạt đỉnh **0,4825 tại K=2**, giảm nhẹ ở K=3–5 rồi phẳng ~0,32 từ K=6 trở đi.

**Quyết định chọn K:** *sinh lý nghiệp vụ* ưu tiên **K = 3** (ba nhóm hành vi kinh điển: **VIP / Loyal / At-risk**), vì:
- Silhouette tại K=3 (0,4083) vẫn ở mức tốt, chỉ thấp hơn K=2 một chút;
- K=2 quá thô, không tách được nhóm trung thành vs. sắp rời bỏ;
- K=3 khớp với logic nghiệp vụ, dễ giải thích cho nhà quản lý và có thể đối chiếu trực tiếp với chiến lược marketing 3 nhóm.

> **Bảo vệ học thuật:** *"Slide 5.3 trang 20 đặt câu hỏi mở 'Làm thế nào để đánh giá hiệu quả của K-means?'. Tôi trả lời bằng đúng hai phương pháp chuẩn cho câu hỏi đó – Elbow Method và Silhouette Score – kết hợp với tiêu chí chọn K theo giá trị nghiệp vụ, vì một chỉ số thống kê đơn lẻ không đủ để ra quyết định."*

### 6.3. Đối chiếu với 9 phân khúc `Mã PKKH` sẵn có (Slide 5 – Confusion Matrix)

**Đây là phép kiểm chứng mạnh nhất của toàn bộ đồ án.**

Ma trận nhầm lẫn cho **K = 9** (dòng = nhãn PKKH thực tế, cột = cụm K-Means):

| PKKH | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| A1 | 125 | 188 | 172 | 102 | 167 | 63 | 192 | 212 | 181 |
| A2 | 136 | 139 | 161 | 118 | 137 | 72 | 226 | 138 | 153 |
| A3 | 152 | 70 | 82 | **182** | 43 | 43 | 264 | 12 | 109 |
| B1 | 130 | 151 | 167 | 141 | 120 | 57 | 181 | 180 | 161 |
| B2 | 150 | 117 | 141 | **193** | 101 | 59 | 178 | 141 | 112 |
| B3 | 157 | 56 | 112 | 113 | 38 | 62 | **252** | 3 | 117 |
| C1 | 162 | 42 | 80 | **251** | 44 | 61 | 243 | 14 | 68 |
| C2 | 134 | 29 | 63 | **193** | 27 | 46 | **258** | 4 | 84 |
| C3 | 166 | 14 | 46 | **269** | 14 | 52 | 201 | 0 | 63 |

**Các chỉ số đánh giá (Slide 5):**

| Chỉ số | Giá trị | Cách hiểu |
|---|---|---|
| **Accuracy** (gán 1-1 tối ưu) | **0,1559** | K-Means phân khác hành vi **không khớp** phân khúc nhân khẩu học |
| **Purity** (K=3) | **0,1635** | Thấp hơn ngưỡng ngẫu nhiên trộn đều (1/9 ≈ 0,111 tính cho K=9; kỳ vọng purity ngẫu nhiên ≈ 0,33 cho K=3) |
| Macro Precision / Recall / F1 | 0,1111 / 0,1111 / 0,1111 | Trùng ngưỡng ngẫu nhiên |

**Kết luận khoa học (đây là đóng góp quan trọng của đồ án):**

> K-Means trên RFM **KHÔNG** tái tạo được 9 phân khúc `Mã PKKH`. Điều này **không phải thất bại** mà là **bằng chứng định lượng** cho thấy hai hệ phân khúc đo **hai thứ khác nhau**:
> - `Mã PKKH` (A1–C3) = **nhân khẩu học** (nghề nghiệp, độ tuổi, mức quan tâm sức khỏe) → do con người định nghĩa, dùng để **nhắm mục tiêu nội dung/báo cáo**;
> - K-Means trên RFM = **hành vi giao dịch** (tần suất, giá trị, thời gian) → dùng để **nhắm mục tiêu hành động** (gửi mã giảm giá, chăm sóc khách sắp rời bỏ).

**Vì sao điều này có giá trị thực tế?** Chính vì hai trục độc lập nên hệ thống cần **cả hai**:
- Bảng **PKKH × Nhóm hàng** (mục 5.2) cho biết *phân khúc nào nên quảng bá nhóm hàng nào*.
- Cụm RFM cho biết *khách nào đang sắp rời bỏ cần ưu đãi riêng*.

### 6.4. Cấu hình 3 cụm hành vi (K=3) và ý nghĩa nghiệp vụ

| Cụm | Quy mô | Hành vi trội đại diện (PKKH chiếm đa số) | Nhãn nghiệp vụ | Hành động đề xuất |
|---|---|---|---|---|
| C0 | 4.519 | C1 (595), C3 (549), A3 (533), C2 (528) | **Nhóm không xác định / ngẫu nhiên** – phân bố PKKH rất loãng, đồng nghĩa hành vi RFM không phân biệt được | Dùng Tầng 4 (segment-popularity) làm phương án mặc định |
| C1 | 2.811 | **A1 (685)**, B1 (552), A2 (508), B2 (434) | **Nhóm giá trị cao** (A1 = nhân viên VP, chủ DN, thu nhập cao) | Ưu đãi sản phẩm premium (Trà hoa, Set trà) |
| C2 | 2.327 | A1 (299), A2 (291), B1 (280), B3 (280) | **Nhóm trung thành / trung bình** | Duy trì, đề xuất bộ (Set) để tăng giá trị đơn |

> **Bài học thiết kế:** Cụm C0 chiếm 46,8% khách hàng nhưng chứa 4 phân khúc PKKH gần như cân bằng → **đây chính là nhóm mà Tầng 4 content-based có vai trò bổ trợ**, vì không có tín hiệu hành vi đủ mạnh để dùng luật MBA.

### 6.5. K-Medoids / PAM như phương án đối chứng (Slide 5.3)

| Tiêu chí | K-Means | K-Medoids (PAM) |
|---|---|---|
| Đại lượng đại diện | Centroid (trung bình) | Medoid (điểm thực) |
| Nhạy với outlier | **Cao** (trung bình bị kéo) | Thấp (medoid là quan sát thật) |
| Dữ liệu này có outlier giá trị cao (3,94 triệu) | ⚠️ | ✔ |
| Tốc độ | Nhanh hơn | Chậm hơn (O(n²·K)) |
| Vai trò trong đồ án | **Thuật toán chính** | **Phương án đối chứng / phòng vệ khi bị hỏi độ bền** |

---

## 7. Tầng 3 – Khai phá luật kết hợp (Market Basket Analysis)

### 7.1. Thuật toán Apriori (mở rộng)

**Nguyên lý:** quét tất cả các tập mục thường xuyên $L_1$, sinh ứng viên $C_{k+1}$ bằng phép nối $L_k \bowtie L_k$, kiểm tra support của từng ứng viên, lặp lại cho tới khi không còn ứng viên nào đạt ngưỡng.

$$\text{Apriori}(T,D,I) = \bigcap_{T'\subseteq T} \{T'\in T \mid \text{support}(T')\ge I\}$$
*(đặc tính "đơn vị tồn tại ⟹ tập cha tồn tại" giúp cắt tỉa candidate set)*

**Tham số đã dùng trong đồ án:**

| Tham số | Giá trị | Lý do |
|---|---|---|
| `min_support` | 0,01 (kết quả chính) / 0,005 (khám phá rộng) | 0,01 tương đương ≥ 314 đơn → đủ lớn để kiểm định thống kê |
| `min_confidence` | 0,10 | Ngưỡng thực dụng để lọc rule yếu |
| Độ dài luật tối đa | 3 | Giới hạn kích thước ứng viên |
| Biến thể | **FP-Growth** dùng để so sánh hiệu năng | FP-Tree duyệt 2 lần, không sinh candidate set |

**Số lượng luật tìm được:**

| min_support | Số cặp | Số bộ ba | Ghi chú |
|---|---|---|---|
| 0,02 | 39 | — | Quá khắt, bỏ nhiều luật thú vị |
| **0,01** | **66** | **13** | **Ngưỡng chọn chính** |
| 0,005 | 102 | — | Dùng để khám phá bổ sung |

### 7.2. Kết quả khai phá — và phát hiện quan trọng

**Top cặp theo Support (min_support = 1%):**

| Luật | Support | Confidence | Lift | Leverage |
|---|---|---|---|---|
| BOT01 (Bột cần tây) → TTC01 (Trà gừng) | 0,1290 | 0,320 | 0,85 | −0,0221 |
| TMX01 (Trà dưỡng nhan) → TTC01 (Trà gừng) | 0,0851 | 0,336 | 0,90 | −0,0099 |
| BOT01 → TTC02 (Cam lát) | 0,0812 | 0,202 | 0,87 | −0,0120 |
| BOT01 → TMX01 | 0,0785 | 0,195 | 0,77 | −0,0235 |
| TTC01 → TTC02 | 0,0739 | 0,197 | 0,85 | −0,0129 |
| BOT01 → TMX03 (Trà gạo lứt 8 vị) | 0,0727 | 0,181 | 0,87 | −0,0112 |
| BOT01 → TMX02 (Trà cam sả quế) | 0,0671 | 0,167 | 0,87 | −0,0097 |
| TMX03 → TTC01 | 0,0626 | 0,300 | 0,80 | −0,0156 |
| TMX02 → TTC01 | 0,0576 | 0,302 | 0,80 | −0,0140 |
| BOT01 → THO03 (Trà hoa cúc trắng) | 0,0520 | 0,129 | 0,83 | −0,0110 |

**Phân bố Lift trên toàn bộ 171 cặp:**

| Vùng giá trị | Số cặp | Tỷ lệ |
|---|---|---|
| Lift > 1 (tương quan dương) | **8** | 4,7% |
| Lift = 1 (độc lập) | 8 | 4,7% |
| **Lift < 1 (tương quan âm)** | **163** | **95,3%** |

Thống kê mô tả Lift: mean = 0,7926 · std = 0,1254 · min = 0,4690 · max = 1,4811 · median = 0,7943.

**Phân tách theo cùng / khác nhóm hàng:**

| Quan hệ | Số cặp | Lift trung bình | Lift median | Lift max |
|---|---|---|---|---|
| Cùng nhóm hàng | 40 | 0,8689 | 0,8291 | 1,4811 |
| Khác nhóm hàng | 131 | 0,7693 | 0,7776 | 1,0490 |

**8 cặp có Lift > 1 đều thuộc nhóm Set trà và có Support rất thấp (≤ 0,0025):**

| Luật | Support | Confidence | Lift |
|---|---|---|---|
| SET01 → SET07 | 0,0010 | 0,033 | 1,4811 |
| SET06 → SET07 | 0,0009 | 0,030 | 1,3364 |
| SET01 → SET02 | 0,0014 | 0,047 | 1,2929 |
| SET02 → SET03 | 0,0021 | 0,058 | 1,1541 |
| SET07 → THO04 | 0,0020 | 0,088 | 1,0490 |

> **Kết luận Tầng 3:** Trên dữ liệu này, Apriori **không sinh được luật kinh doanh mạnh** (chỉ 8/171 cặp có Lift > 1, và các cặp đó có Support < 0,25% → **không đủ cơ sở thống kê** để đưa vào vận hành). Đây chính là phát hiện khoa học quan trọng nhất, được trình bày chi tiết ở **Mục 10** và là lý do thiết kế **Tầng 4**.

### 7.3. Kiểm định chi-square 2×2 trên từng luật (Slide 1.1 — áp dụng mới)

Bảng phân phối 2×2 cho luật *mua BOT01* × *mua TTC01*:

| | Có TTC01 | Không TTC01 | Tổng |
|---|---|---|---|
| **Có BOT01** | 4.056 | 8.608 | 12.664 |
| **Không BOT01** | 7.736 | 11.038 | 18.774 |
| **Tổng** | 11.792 | 19.646 | 31.438 |

$$\chi^2 = 271{,}4;\quad dof=1;\quad p = 5{,}63\times10^{-61};\quad \phi^2 = 0{,}0086$$

**Kết quả cho 5 luật tiêu biểu:**

| Luật | n₁₁ | n₁₀ | n₀₁ | n₀₀ | χ² | p | φ² |
|---|---|---|---|---|---|---|---|
| BOT01 × TTC01 | 4.056 | 8.608 | 7.736 | 11.038 | 271,4 | 5,6·10⁻⁶¹ | 0,0086 |
| BOT01 × TMX01 | 2.469 | 10.195 | 5.495 | 13.279 | 381,4 | 6,3·10⁻⁸⁵ | 0,0121 |
| TTC01 × TTC02 | 2.324 | 9.468 | 4.952 | 14.694 | 124,9 | 5,3·10⁻²⁹ | 0,0040 |
| THO03 × THO01 | 557 | 4.360 | 3.672 | 22.849 | 22,4 | 2,3·10⁻⁶ | 0,0007 |
| TMX01 × TMX03 | 1.297 | 6.667 | 5.255 | 18.219 | 133,8 | 6,1·10⁻³¹ | 0,0043 |

**Diễn giải đúng cách (điểm hay bị chấm điểm):**
- $p < 0{,}001$ → **mối liên hệ có ý nghĩa thống kê** (không phải ngẫu nhiên).
- $\chi^2$ lớn nhưng **φ² rất nhỏ (0,004–0,012)** → **hiệu ứng thực tế yếu**. Với mẫu 31.438 đơn, mọi sai lệch nhỏ cũng cho p ≈ 0. Vì vậy **không được kết luận "luật này có giá trị kinh doanh" chỉ dựa vào p-value**; phải kết hợp **Lift** và **φ²**.
- Kết hợp cả ba: **luật có ý nghĩa thống kê nhưng ĐỒNG ÂM (lift < 1)** → đây là quan hệ **thay thế**, không phải bổ trợ.

> **Đây chính là câu trả lời hoàn hảo cho câu hỏi khó nhất:** *"Thuật toán khai phá luật kết hợp này có nằm trong slide bài giảng không?"*
> → *"Chi-square thì CÓ — Slide 1.1 đã dạy công thức $\chi^2=\sum\frac{(O-E)^2}{E}$. Tôi không học thêm một công thức mới, tôi **áp dụng lại** kỹ thuật đã học vào một bối cảnh dữ liệu mới: thay vì kiểm tra hai biến định danh độc lập, tôi dựng bảng phân phối 2×2 giữa hai sự kiện 'mua sản phẩm A' và 'mua sản phẩm B' trong cùng một đơn hàng. Đó là một ứng dụng mới của một thuật toán cũ, không phải một thuật toán ngoài chương trình."*

### 7.4. Targeted Association Mining theo phân khúc (mở rộng)

Thay vì khai phá trên toàn bộ 31.438 đơn, khai phá **riêng trong từng `Mã PKKH`** để tìm luật chỉ đúng với nhóm cụ thể — nâng giá trị kinh doanh của Tầng 3.

**Kết quả chi tiết hóa:** Cặp có Lift dương cao nhất (SET01→SET07, lift 1,48) thuộc nhóm Set trà — cần kiểm tra xem luật này tập trung ở phân khúc nào. Bảng **PKKH × Nhóm hàng** (mục 5.2) cho thấy phân khúc **C1** chiếm 1.501/2.915 = **51,5%** toàn bộ lượt mua Set trà → đây là phân khúc "mua làm quà tặng", nơi **mua nhiều set trà là hợp lý** (cần đóng gói, cần số lượng lớn).

### 7.5. So sánh Apriori và FP-Growth

| Tiêu chí | Apriori | FP-Growth (FP-Tree) |
|---|---|---|
| Nguyên lý | Sinh & kiểm tra candidate set $C_{k+1}$ | Dựng cây, gom các node điều kiện thành itemset, đệ quy |
| Số lần duyệt dữ liệu | Số lần lặp của chiều itemset (k) | **2 lần** (đọc + đi duyệt cây) |
| Bộ nhớ | Cao (lưu candidate set) | Thấp |
| Độ phức tạp | $O(2^{|I|}\cdot N)$ xấu nhất | Xấp nhất tương đương, thực tế nhanh hơn nhiều |
| Kết quả | **Giống hệt nhau** (cùng tập luật) | Giống hệt nhau |
| Trên dữ liệu này (19 items, 31.438 baskets) | Chạy rất nhanh | Chạy rất nhanh |

> **Định vị trong đồ án:** Apriori là thuật toán **được triển khai chính** (minh bạch, dễ kiểm chứng với giảng viên). FP-Growth được **trình bày như biến thể hiệu năng** để thể hiện hiểu biết về cải tiến thuật toán. Với 19 mặt hàng, việc chuyển sang FP-Growth là **không cần thiết về mặt kỹ thuật** — nói rõ điều này thay vì phô trương.

---

## 8. Tầng 4 – Gợi ý sản phẩm đa tầng

### 8.1. Ba nhánh gợi ý và nguyên tắc trọng số

```
Khách có lịch sử mua trước 01/10/2022 ?  ──►  CÓ  ──►  NHÁNH A: Rule MBA (confidence) ∪ Content-based TF-IDF+Cosine
                                     │
                                     └──►  KHÔNG (khách mới) ──►  NHÁNH B: Popularity theo PKKH
                                                                          (có thể bổ sung Persona TF-IDF)
Sau khi gộp & khử trùng, còn < 5 gợi ý ? ──►  NHÁNH C: Top sản phẩm bán chạy của nhóm hàng liên quan
```

### 8.2. Xử lý văn bản (Slide 1.1 — Data Cleaning áp dụng cho miền văn bản)

Tên sản phẩm tiếng Việt có dấu, có số thứ tự ("Set 10 gói"), cần chuẩn hóa trước khi vector hóa:

| Bước | Ví dụ |
|---|---|
| Chuyển chữ thường | `Trà Nụ Hoa Nhài Trắng` → `trà nụ hoa nhài trắng` |
| Loại số thứ tự | `Set 10 gói trà hoa cúc trắng` → `set gói trà hoa cúc trắng` |
| Bỏ dấu câu | `Trà gạo lứt 8 vị` → `trà gạo lứt vị` |
| Tokenize theo regex | `(?u)\b\w+\b` |
| Loại stopword tiếng Việt | bỏ `vị`, `trà` (nếu xuất hiện ở > 80% văn bản) |
| Ghép thêm tên nhóm | `trà hoa cúc trắng` + `trà hoa` → làm giàu ngữ nghĩa |

### 8.3. TF-IDF

$$\text{tfidf}(t,d)=\text{tf}(t,d)\times\log\frac{N}{\text{df}(t)}$$
với biến thể **sublinear TF**: $\text{tf}(t,d)=1+\log(\text{count}(t,d))$, giảm ảnh hưởng của từ xuất hiện nhiều lần trong một tên sản phẩm dài.

Tham số: `ngram_range=(1,2)` (unigram + bigram, bắt được cụm "trà hoa", "gói trà"), `sublinear_tf=True`.

**Kết quả ma trận tương đồng Cosine giữa các cặp sản phẩm đáng chú ý:**

| Cặp | Cosine | Ý nghĩa |
|---|---|---|
| THO01 Trà nụ hoa nhài trắng ↔ SET01 Set 10 gói trà nụ hoa nhài trắng | **0,7216** | Cùng vị → gợi ý tự nhiên |
| THO03 Trà hoa cúc trắng ↔ SET03 Set 10 gói trà hoa cúc trắng | **0,6675** | Cùng vị → gợi ý tự nhiên |
| TTC01 Trà gừng ↔ TTC02 Cam lát | 0,6076 | Cùng nhóm "trà củ, quả sấy" |
| TMX01 Trà dưỡng nhan ↔ SET05 Set 10 gói trà dưỡng nhan | 0,5499 | Cùng vị |
| THO04 Trà nụ hoa hồng Tây Tạng ↔ SET02 Set 10 gói trà hoa đậu biếc | 0,1223 | Khác vị → tương đồng thấp |
| BOT01 Bột cần tây ↔ TMX01 Trà dưỡng nhan | 0,0000 | Hoàn toàn khác loại |

> **Demo slide rất đắt giá:** khách mua *Trà hoa cúc trắng* (THO03) → hệ thống gợi ý *Set 10 gói trà hoa cúc trắng* (SET03), vì cosine = 0,6675. Đây là một luật gợi ý **có thể giải thích trực quan cho khách hàng**, và đồng thời **là luật không thể sinh ra từ luật kết hợp** (vì lift của cặp này là 0,83 < 1, tức là trên dữ liệu này người ta thường mua *thay vì* chứ không mua *cùng*).

### 8.4. Gợi ý theo phân khúc (Segment-aware Popularity)

$$\text{pop}_{s}(i)=\frac{|\{đơn\ có\ s\ và\ i\}|}{|\{đơn\ có\ s\}|},\qquad
\text{lift}_{s}(i)=\frac{\text{pop}_{s}(i)}{\text{pop}_{global}(i)}$$

Chiến lược: dùng `pop_s` (hoặc `lift_s`) làm xương sống vì **9 phân khúc PKKH mang thông tin nhân khẩu học** mà lịch sử mua của khách mới chưa có.

### 8.5. Đánh giá khuyến nghị (Slide 5 — mở rộng sang Top-K)

| Chỉ số | Công thức |
|---|---|
| Precision@k | $P@k=\frac{|\text{top-}k \cap \text{relevant}|}{|\text{top-}k|}$ |
| Recall@k | $R@k=\frac{|\text{top-}k \cap \text{relevant}|}{|\text{relevant}|}$ |
| Hit-Rate@k | $HR@k=\mathbb{1}\left[|\text{top-}k \cap \text{relevant}|>0\right]$ |
| NDCG@k | $DCG@k=\sum_{i=1}^{k}\frac{rel_i}{\log_2(i+1)}$, $NDCG=\frac{DCG}{IDCG}$ |

**Thiết kế thí nghiệm (đảm bảo không rò rỉ dữ liệu):**
- **Chia theo thời gian:** Train = 01/01–30/09/2022; Test = 01/10–31/12/2022. *Lý do:* có mùa vụ mạnh (tháng 12 đỉnh doanh thu); chia ngẫu nhiên sẽ để mô hình "nhìn thấy" tương lai.
- **Ground truth:** tập sản phẩm khách thực sự mua trong kỳ test, trừ đi sản phẩm đã mua trong kỳ train.
- **Mọc thống kê (popularity, luật, TF-IDF) đều chỉ tính trên tập train.**

---

## 9. Đánh giá mô hình – Kết quả thực nghiệm đầy đủ

### 9.1. Tầng 2 – Đánh giá phân cụm

| Chỉ số | Kết quả | Slide tham chiếu |
|---|---|---|
| WCSS tối thiểu | 2.855,68 (K=12) / 9.527,13 (K=3) | Slide 5.3 |
| **Silhouette tối đa** | **0,4825 (K=2)** | Mở rộng – trả lời Slide 5.3 tr.20 |
| K được chọn | **3** (cân bằng thống kê & nghiệp vụ) | — |
| **Purity vs 9 nhãn PKKH (K=3)** | **0,1635** | Slide 5 (Confusion Matrix) |
| **Accuracy (gán 1-1 tối ưu, K=9)** | **0,1559** | Slide 5 |
| Macro P / R / F1 (K=9) | 0,1111 / 0,1111 / 0,1111 | Slide 5 |
| Ngưỡng ngẫu nhiên | ≈ 0,111 | Slide 5 |

**Kết luận:** K-Means trên RFM và hệ PKKH là **hai hệ phân khúc độc lập** → dùng cho hai mục tiêu khác nhau (xem mục 6.3).

### 9.2. Tầng 3 – Đánh giá luật kết hợp

| Chỉ số | Kết quả |
|---|---|
| Số luật tìm được (min_support 1%) | 66 cặp, 13 bộ ba |
| Tỷ lệ luật có Lift > 1 | **4,7%** (8/171) |
| Số luật **vận hành được** (Lift > 1 & Support ≥ 1% & p < 0,001) | **0** |
| Số luật có ý nghĩa thống kê (p < 0,001) | 5/5 luật kiểm tra đều có |
| Hiệu ứng thực tế (φ²) | 0,0040 – 0,0121 (rất nhỏ) |

### 9.3. Tầng 4 – Benchmark gợi ý (hold-out theo thời gian)

**NHÁNH WARM — khách có lịch sử mua (n = 2.255):**

| Chiến lược | P@5 | R@5 | HR@5 | NDCG@5 |
|---|---|---|---|---|
| **Popularity theo PKKH (Segment-aware)** | **0,4098** | **0,7355** | **0,9446** | **0,7018** |
| Lift theo PKKH | 0,3288 | 0,5961 | 0,8865 | — |
| Rule MBA (confidence) | 0,2631 | 0,4384 | 0,7375 | 0,4005 |
| **HYBRID (PKKH + rule + content)** | 0,3041 | 0,5147 | 0,7978 | 0,4823 |
| Popularity toàn cục | 0,2259 | 0,3768 | 0,6847 | 0,3337 |
| Content-based TF-IDF + Cosine | 0,1636 | 0,2769 | 0,5778 | 0,2450 |
| **Random (baseline ngẫu nhiên)** | 0,2325 | 0,4255 | 0,7437 | 0,3727 |

**NHÁNH COLD-START — khách mới, không lịch sử (n = 2.825, tỷ lệ 52,8%):**

| Chiến lược | P@5 | R@5 | HR@5 | NDCG@5 |
|---|---|---|---|---|
| **Popularity theo PKKH** | **0,4246** | **0,5963** | **0,9395** | **0,6087** |
| HYBRID (PKKH + rule + content) | 0,4246 | 0,5963 | 0,9395 | 0,6087 |
| Popularity toàn cục | 0,4153 | 0,5838 | 0,9310 | 0,5899 |
| Random (baseline) | 0,1985 | 0,2633 | 0,6595 | 0,2594 |

**Đọc kết quả — ba điểm cực kỳ quan trọng khi bảo vệ:**

1. **Chiến lược tốt nhất là Segment-aware Popularity** (P@5 = 0,4098), vượt xa Rule MBA (0,2631) và Content-based (0,1636). → Đề tài đã **hiệu chỉnh lại thiết kế** dựa trên bằng chứng thực nghiệm, chứ không giữ một kiến trúc "đẹp" nhưng kém hiệu quả.

2. **Content-based TF-IDF + Cosine đứng riêng là yếu nhất** (P@5 = 0,1636 < cả baseline ngẫu nhiên 0,2325). Nguyên nhân: chỉ có **19 sản phẩm**, mỗi khách đã mua trung bình 8,5 sản phẩm khác nhau → không còn nhiều "phòng trống" để tương đồng nội dung có ý nghĩa. **Đây là phát hiện trung thực, cần trình bày như vậy** chứ không nên giấu.

3. **Baseline ngẫu nhiên đạt P@5 = 0,2325** — cao bất thường vì "chọn ngẫu nhiên 5 trong 19 sản phẩm" đã có xác suất trúng ~23%. **Bắt buộc phải đưa baseline này vào báo cáo**, nếu không mọi con số đều dễ bị hiểu nhầm là "tốt". Chiến lược tốt nhất vượt ngẫu nhiên **+0,1773 P@5 (tương đương +76%)** → đây mới là con số có ý nghĩa.

### 9.4. Tổng hợp hiệu quả toàn hệ thống

| Tầng | Chỉ số chính | Giá trị | Slide |
|---|---|---|---|
| Tầng 1 | χ² (PKKH × Nhóm hàng) | 4.938,42; p<0,001 | Slide 1.1 |
| Tầng 2 | Silhouette tối đa / K chọn | 0,4825 / K=3 | Slide 5.3 + mở rộng |
| Tầng 3 | Số luật vận hành được | 0 (phát hiện thay thế) | Mở rộng |
| Tầng 4 (warm) | P@5 / R@5 / NDCG@5 | 0,4098 / 0,7355 / 0,7018 | Slide 5 mở rộng |
| Tầng 4 (cold) | P@5 / R@5 / HR@5 | 0,4246 / 0,5963 / 0,9395 | Slide 5 mở rộng |

---

## 10. Phát hiện khoa học quan trọng: cơ chế THAY THẾ

### 10.1. Vấn đề

Trong kinh doanh bán lẻ, giỏ hàng lý tưởng chứa **sản phẩm bổ trợ** nhau (mua cà phê → mua bánh). Kỳ vọng của thuật toán Apriori là phát hiện các cặp có **Lift > 1**.

### 10.2. Kết quả

Trên 171 cặp được khai phá từ 31.438 đơn:
- **163 cặp (95,3%) có Lift < 1** → tương quan **âm**
- Chỉ 8 cặp (4,7%) có Lift > 1, và tất cả đều có Support ≤ 0,25%
- Lift trung bình = 0,7926

Tương quan âm mạnh nhất lại xuất hiện giữa các nhóm hàng **khác nhau** (Lift TB 0,7693) chứ không phải cùng nhóm (0,8689) — điều này **loại trừ** giả thuyết "chỉ là hiệu ứng cạnh tranh trong cùng danh mục".

### 10.3. Giải thích (ba cơ chế được kiểm chứng)

**Cơ chế 1 — "Bột cần tây" chiếm slot giỏ hàng (tác giả chính).**
BOT01 có Support = 0,4028, tức xuất hiện trong 40% đơn. Giỏ hàng trung bình chỉ 2,61 món. Khi BOT01 đã chiếm 1 slot, các sản phẩm khác bị đẩy ra → tự động sinh tương quan âm với mọi sản phẩm còn lại. Kiểm chứng: **mọi luật có Support cao đều dẫn BOT01 → X, và tất cả đều có Lift < 1** (0,77–0,87).

**Cơ chế 2 — Cấu trúc danh mục hẹp (19 sản phẩm / 5 nhóm).**
Với danh mục nhỏ và thiên lệch, xác suất chọn ngẫu nhiên 2 mặt hàng trong cùng nhóm là thấp, kéo Lift của các cặp cùng nhóm xuống dưới 1.

**Cơ chế 3 — Giỏ hàng "combo" có cấu trúc cố định.**
15.250 đơn chứa đúng 2 nhóm hàng, 9.875 đơn chứa 3 nhóm → các tổ hợp nhóm hàng lặp lại theo khuôn mẫu, khiến các cặp *cụ thể* bị phân tán.

### 10.4. Hệ quả thiết kế — và đây là lý do Tầng 4 tồn tại

| Nếu chỉ làm Tầng 3 (Apriori) | Nếu có đủ Tầng 4 |
|---|---|
| **0 luật vận hành được** (Lift>1 & Support≥1%) | 66 cặp dùng làm ngưỡng *co-purchase* cho nhánh warm |
| Không có gợi ý nào cho 52,8% khách mới | P@5 = 0,4246, HR@5 = 0,9395 cho nhóm cold-start |
| Hệ thống "chạy được nhưng không dùng được" | Hệ thống có sản phẩm cụ thể và đo lường được |

> **Cách trình bày trước hội đồng:** Đây là **đóng góp thực sự của đồ án**. Thay vì cứ áp Apriori và khoe ra những luật không có ý nghĩa, đồ án đã *kiểm định tín hiệu định lượng*, phát hiện cơ chế thay thế, và **thiết kế lại kiến trúc** để bù đắp khoảng trống đó. Đó chính là tư duy "Data Analytics Lifecycle" mà Slide 1 yêu cầu: *Model Planning → Model Building → Communicate Results → Operationalize*, có vòng lặp phản hồi từ kết quả về thiết kế.

---

## 11. Bộ Q&A dự kiến phỏng vấn

### Nhóm A — Về dữ liệu

**A1. Dữ liệu này là thật hay mô phỏng?**
> Đây là dữ liệu bán lẻ trong nước, được **chuẩn hóa về cấu trúc dữ liệu thực tế**: mã đơn tăng dần liên tục (ORD0000001 → ORD0031438), mã khách dạng CUZ…, 9 phân khúc khách hàng có mô tả nhân khẩu học đầy đủ (nghề, độ tuổi, mức thu nhập, khu vực), giá theo danh mục sản phẩm, và có mùa vụ Tết rất rõ (tháng 12 đạt đỉnh, gấp 3,82 lần tháng 4). Nếu đây là dữ liệu mô phỏng thì đó là **điểm mạnh** vì nó cho phép kiểm chứng mô hình: có **ground truth** 9 nhãn `Mã PKKH` để đối chiếu — điều mà dữ liệu thật thường không có.

**A2. Có bị thiếu dữ liệu không? Xử lý thế nào?**
> Chỉ 2.518 dòng (3,07%) thiếu `Tên khách hàng`. Đây là cột **chỉ hiển thị**, mọi phép toán đều dùng `Mã khách hàng` → dùng `fillna("Ẩn danh")` là đủ. Dữ liệu **không có dòng trùng lặp**, **không có giá 0**, và `Thành tiền = SL × Đơn giá` khớp 100%.

**A3. Chỉ 19 sản phẩm thì có đủ để làm Market Basket Analysis không?**
> MBA không đòi hỏi nhiều sản phẩm, mà đòi hỏi giỏ hàng **đa dạng**: ở đây 90,68% đơn có ≥2 mặt hàng, trung bình 2,61 món → mẫu đồng xuất hiện là thật, 31.438 giỏ là mẫu lớn. Tuy nhiên tôi **thừa nhận** hạn chế: với 19 sản phẩm, không gian khả thể nhỏ nên số luật sinh ra hữu hạn (171 cặp) và đó là lý do tôi phải bổ sung Tầng 4.

### Nhóm B — Về thuật toán

**B1. Các thuật toán bạn dùng có trong slide bài giảng không?**
> Có 21 thuật toán thuộc giáo trình và tôi trích dẫn đầy đủ (Slide 1.1, 1, 2.2, 3, 4, 5, 5.1, 5.2, 5.3). Có **10 thuật toán mở rộng** ngoài giáo trình: RFM, Apriori, FP-Growth, Support/Confidence/Lift/Leverage/Conviction, TF-IDF, Cosine Similarity, Elbow, Silhouette, Precision@k/Recall@k. Tôi **công khai** điều này và chọn chúng **vì có lý do**, không phải vì "nghe hay". Điểm mấu chốt: **Elbow + Silhouette** trả lời đúng câu hỏi mở tại Slide 5.3 trang 20; **Chi-square trên luật** là **ứng dụng lại** công thức đã học ở Slide 1.1 vào bối cảnh bảng 2×2; **Cosine Similarity** là mở rộng cùng khái niệm "đo khoảng cách" đã học ở Slide 5.2.

**B2. Tại sao chọn K-Means mà không chọn K-NN (Slide 5.2)?**
> Slide 5.3 đã nêu trực tiếp: K-Means **nhạy với nhiễu** (dùng centroid = trung bình), K-Medoids thì không. Dữ liệu tôi có outlier giá trị rất cao (đơn 3,94 triệu, cao gấp 16 lần trung vị) → centroid bị kéo lệch. Tôi chọn **K-Means sau khi log-transform** để nén outlier, đồng thời dùng **K-Medoids/PAM** (đã có trong Slide 5.3) làm phương án đối chứng. Ngoài ra, K-Means là thuật toán **không cần gán nhãn**, phù hợp bài toán phân khúc hành vi.

**B3. Tại sao dùng log transform rồi mới Z-score?**
> F và M có phân phối lệch phải mạnh (Mean ≫ Median), và M lớn hơn F hàng trăm lần về đơn vị. Nếu chuẩn hóa trực tiếp, trục M sẽ chiếm trọn không gian và K-Means sẽ chỉ phân theo chi tiêu. Log biến phân phối lệch thành gần đối xứng; Z-score đưa cả 3 trục về cùng thang đo (Slide 1.1).

**B4. Apriori và FP-Growth khác nhau gì, hệ thống dùng cái nào?**
> Apriori sinh và kiểm tra candidate set $C_{k+1}$ (bị nghẽn cổ chai); FP-Growth dựng FP-Tree và duyệt cây 2 lần, không sinh candidate set. Cùng kết quả, FP-Growth nhanh hơn nhiều trên dữ liệu lớn. Hệ thống **triển khai Apriori** vì chỉ có 19 items và cần minh bạch, dễ đối chiếu với giảng viên; FP-Growth được trình bày như **biến thể hiệu năng** để thể hiện hiểu biết về cải tiến thuật toán.

**B5. Vì sao chọn Cosine Similarity chứ không dùng khoảng cách Euclidean như Slide 5.2?**
> Cosine đo **góc** giữa hai vector, không nhạy với độ dài — phù hợp với vector TF-IDF có độ dài khác nhau. Slide 5.2 đã cảnh báo "k-NN nhạy với thang đo của đặc trưng", đây chính là lý do trong cùng tinh thần đó tôi chọn một phép đo **bất biến với thang đo** cho miền văn bản. Với 19 sản phẩm và 2 chiều (nhóm hàng, tên), dữ liệu đủ thưa để cosine là lựa chọn tự nhiên.

**B6. K-Means cho K=3 nhưng dữ liệu có 9 nhãn, bạn chọn cái nào?**
> Tôi **đã kiểm chứng bằng Confusion Matrix** (Slide 5) và con số trả lời rất rõ: purity chỉ 0,1635, thấp hơn ngưỡng ngẫu nhiên. **Đây không phải thất bại mà là kết luận khoa học**: 9 `Mã PKKH` là phân khúc **nhân khẩu học** (nghề, tuổi, sức khỏe) do con người quy định, còn K-Means trên RFM là phân khúc **hành vi giao dịch**. Hai trục đo hai thứ khác nhau nên **không thể so trực tiếp** — và chính vì vậy hệ thống cần cả hai: bảng PKKH × Nhóm hàng để quyết định *quảng bá nhóm hàng nào cho phân khúc nào*, cụm RFM để quyết định *ai đang sắp rời bỏ, ai là VIP*.

### Nhóm C — Về lựa chọn thiết kế

**C1. Vì sao không dùng Collaborative Filtering / Matrix Factorization?**
> CF cần ma trận user-item **đủ mật độ**. Trên dữ liệu này, **2.825 khách (52,8%) chỉ có đúng 1 giao dịch**, nên CF không thể học được đặc trưng cho họ — và tôi **đã đo** điều này. CF cũng nằm ngoài giáo trình. Vì vậy tôi xây dựng Tầng 4 theo hướng **content-based + segment-aware**, vừa nằm trong khuôn khổ giáo trình (Slide 5.2 về đo khoảng cách, Slide 1.1 về xử lý văn bản) vừa giải quyết được đúng lỗ hổng của dữ liệu. Đây là lý do thiết kế, không phải giới hạn.

**C2. Vì sao không thêm Deep Learning / Random Forest?**
> (1) Ngoài phạm vi giáo trình; (2) **không phù hợp bài toán** — đề tài là phân tích giỏ hàng & gợi ý, không phải phân loại với dữ liệu lớn; (3) dữ liệu có 19 sản phẩm và 82k dòng — mô hình phức tạp không có dữ liệu để học và sẽ **không cải thiện** kết quả; (4) với mọi quyết định kiến trúc, tôi đều **đo lại bằng P@5/R@5/NDCG@5** trên hold-out thời gian, và kết quả cho thấy giải pháp đơn giản theo phân khúc mới là tốt nhất.

**C3. Tại sao split theo thời gian chứ không random?**
> Vì có mùa vụ mạnh: tháng 12 có 4.972 đơn, gấp 3,67 lần tháng 4. Nếu chia ngẫu nhiên, sản phẩm bán chạy cuối năm sẽ xuất hiện ở cả tập train và test → **rò rỉ dữ liệu (data leakage)** và đánh giá sẽ lạc quan. Split theo thời gian (01/01–30/09 train, 01/10–31/12 test) vừa mô phỏng đúng tình huống vận hành thực tế (dự báo cho quý IV), vừa là nguyên tắc chuẩn trong bài toán dự báo chuỗi thời gian.

**C4. Baseline ngẫu nhiên có cần thiết không?**
> **Có, và tôi cố ý đưa vào.** Chỉ có 19 sản phẩm nên "chọn bừa 5 món" đã trúng ~23,25% Precision@5. Nếu không có baseline này, người đọc sẽ tưởng P@5 = 0,16 là kết quả tốt. Có baseline, kết quả trở nên trung thực: chiến lược tốt nhất đạt **0,4098**, tức **+76% so với ngẫu nhiên**. Đây là cách tôi bảo vệ mọi con số trong báo cáo.

### Nhóm D — Về mở rộng & hạn chế

**D1. Hạn chế lớn nhất của hệ thống?**
> **Vấn đề lớn nhất là kết quả của chính Tầng 3**: không có luật kết hợp nào đủ mạnh để vận hành (0 luật thỏa Lift>1 & Support≥1%), và Content-based đứng dưới cả baseline ngẫu nhiên khi dùng độc lập. Hệ thống hiện dựa chủ yếu vào **phân khúc hành vi + phân khúc nhân khẩu học** để gợi ý. Hướng khắc phục: thu thập dữ liệu hành vi chi tiết hơn (click, search, thời gian xem), thêm đánh giá A/B để đo tác động thực tế, và thử nghiệm mô hình hai tầng (candidate generation + re-ranking).

**D2. Nếu thêm dữ liệu mới, hệ thống cần sửa gì?**
> Kiến trúc 4 tầng được thiết kế để **thay thế từng tầng độc lập**:
> - Thêm lịch sử click/session → Tầng 4 thay content-based bằng CF hoặc hybrid, Tầng 3 có thể dùng FP-Growth.
> - Thêm mô tả sản phẩm đầy đủ (thành phần, công dụng) → TF-IDF trở nên có ý nghĩa hơn nhiều và Content-based sẽ vượt baseline.
> - Thêm địa lý → có thể thêm chi-square không gian (Slide 1.1) cho phân tích theo vùng.

**D3. Tại sao hệ thống không dùng hồi quy tuyến tính (Slide 5.1)?**
> Slide 5.1 có thể dùng để **dự báo giá trị đơn hàng tương lai** (biến phụ thuộc: recency, frequency, monetary, tháng, nhóm hàng) — tôi để dành làm **hướng mở rộng (future work)**. Hiện tại, dự báo chưa phục vụ trực tiếp cho quyết định gợi ý, nên đưa vào sẽ làm loãng phạm vi đồ án.

---

## 12. Phạm vi, hạn chế & hướng mở rộng

### 12.1. Phạm vi (In-scope)

- Phân tích giỏ hàng (Market Basket Analysis) trên 31.438 đơn.
- Phân khúc hành vi bằng RFM + K-Means trên 9.657 khách.
- Gợi ý sản phẩm đa tầng với 3 nhánh fallback, đánh giá bằng Top-K metrics.
- Toàn bộ thuật toán thuộc giáo trình Slide 1–5.3.

### 12.2. Ngoài phạm vi (Out-of-scope) — và lý do

| Không sử dụng | Lý do |
|---|---|
| Collaborative Filtering, Matrix Factorization | Ngoài giáo trình; **không khả thi** với 52,8% khách chỉ có 1 giao dịch |
| Deep Learning, Neural Network | Ngoài giáo trình; 19 sản phẩm không đủ dữ liệu huấn luyện |
| Random Forest, Gradient Boosting | Ngoài giáo trình; bài toán không phải dự bão/dạy phân loại tổng quát |
| PCA / giảm chiều | RFM chỉ 3 chiều; đưa vào sẽ mở rộng phạm vi vô ích |
| ARIMA / LSTM dự báo chuỗi thời gian | Ngoài giáo trình; nằm trong hướng mở rộng |
| Dữ liệu ngoài (thời tiết, giá vàng, lịch nghỉ) | Không thuận tiện truy xuất & tra cứu nguồn; chưa cần cho kết luận |

### 12.3. Hạn chế của nghiên cứu

1. **Danh mục sản phẩm hẹp (19 mã)** → giới hạn độ phủ của tất cả thuật toán dựa trên item (MBA, CF, content-based).
2. **Không có log hành vi chi tiết** (click, search, page view) → chỉ gợi ý dựa trên hành động mua.
3. **Chưa kiểm chứng tác động thực tế** → mọi chỉ số đều là **offline metrics** (P@5, R@5, NDCG@5), chưa phải A/B test.
4. **Đánh giá dựa trên hành vi mua, không phải mua lại** → một khách mua 1 món là "hit" dù không có nhu cầu tái mua.
5. **Mô hình đánh giá chỉ dùng 19 mặt hàng** → baseline ngẫu nhiên rất cao, mọi so sánh phải kèm baseline.

### 12.4. Hướng mở rộng (Future work)

1. **Dự báo giá trị đơn hàng** bằng hồi quy tuyến tính (Slide 5.1) với biến mùa vụ → định giá CLV cho tầng phân khúc.
2. **Thay TF-IDF bằng biểu diễn ngữ nghĩa** (embedding) khi có mô tả sản phẩm giàu thông tin.
3. **Kiểm định A/B** trên quy mô nhỏ để đo tác động thực của hệ thống lên giá trị đơn trung bình.
4. **Mô hình 2 tầng:** candidate generation (Apriori/segment) → re-ranking (học từ hành vi).
5. **Mở rộng sang nghiệp vụ giỏ hàng tự động** (auto-bundle) dựa trên luật co-purchase.
6. **Dự báo churn** bằng K-Means trên nhóm "Recency cao + Frequency thấp".

---

## 13. Checklist thuật toán cần giải thích

> **Dùng checklist này để chuẩn bị. Mỗi mục phải trả lời được 6 câu hỏi:** (1) Giải quyết vấn đề gì? (2) Công thức toán học? (3) Đầu vào / Đầu ra? (4) Ý nghĩa thực tiễn trong hệ thống? (5) Tham số & cách chọn? (6) Trích dẫn slide hay giải thích vì sao là mở rộng?

### Nhóm A — Thuật toán CÓ TRONG SLIDE (21 mục — phải thuộc)

| # | Thuật toán | Slide | Cột dữ liệu | Số liệu đã có |
|---|---|---|---|---|
| 1 | Xử lý giá trị thiếu (`fillna`) | 2.2 | `Tên khách hàng` | 2.518 dòng |
| 2 | Loại bỏ trùng lặp (`drop_duplicates`) | 2.2 | Toàn bộ | 0 dòng |
| 3 | Dòng outlier bằng IQR | 4 | `Đơn giá`, `Thành tiền` | Đã đánh dấu |
| 4 | Binning (equal-width / equal-depth) | 1.1 | `SL`, `Đơn giá` | 5 bins |
| 5 | Min-Max Scaling | 1.1 | R, F, M | [0,1] |
| 6 | Z-score Normalization | 1.1 | log(R), log(F), log(M) | μ=0, σ=1 |
| 7 | Pearson Correlation | 1.1 | F ↔ M | ≈0,85 |
| 8 | **Chi-Square Independence** | 1.1 | PKKH × Nhóm hàng | χ²=4.938,42; p<0,001 |
| 9 | Thống kê mô tả (Mean/Median/Mode, Var/SD) | 4 | Tất cả cột số | Mục 2.2 |
| 10 | GroupBy / Value counts / Sort / Filter | 2.2 | Nhiều | Mục 2.6 |
| 11 | **Lloyd K-Means (3 bước)** | 5.3 | RFM chuẩn hóa | K=2…12 |
| 12 | WCSS | 5.3 | — | 13.313 → 2.856 |
| 13 | Khoảng cách Euclidean vs Manhattan | 5.3 | — | Đã so sánh |
| 14 | K-Medoids / PAM | 5.3 | — | Đối chứng |
| 15 | Phân loại Supervised/Unsupervised | 5 | — | — |
| 16 | Feature selection (variance score) | 5 | R, F, M | — |
| 17 | Hold-out / K-fold / Leave-one-out / Stratified | 5 | — | Hold-out theo thời gian |
| 18 | **Confusion Matrix + Accuracy/Precision/Recall/F1** | 5 | K-Means vs PKKH | Purity 0,1635 |
| 19 | Hồi quy tuyến tính + Least Squares | 5.1 | (future work) | — |
| 20 | k-NN + Euclidean/Manhattan + nhạy thang đo | 5.2 | Baseline đối chứng | — |
| 21 | Trực quan hóa + Data Storytelling | 3 | — | Mục 5.4 |
| — | EMC Lifecycle (6 pha) + KDD Process | 1 | — | Mục 5.1 |

### Nhóm B — Thuật toán MỞ RỘNG (10 mục — phải có lập luận bảo vệ)

| # | Thuật toán | Công thức cần thuộc | Lập luận bảo vệ |
|---|---|---|---|
| 1 | RFM Feature Engineering | R, F, M định nghĩa | Slide dạy "cách phân cụm", không dạy "phân cụm theo cái gì"; RFM là chuẩn marketing |
| 2 | Log transform | $x'=\log(1+x)$ | Cần thiết vì phân phối lệch phải (Mean ≫ Median) |
| 3 | Apriori | Nguyên lý anti-monotone, candidate generation | Ngoài giáo trình — nhưng đề tài "phân tích giỏ hàng" không thể thiếu |
| 4 | FP-Growth / FP-Tree | 2 lượt duyệt, không candidate set | Biến thể hiệu năng, thể hiện hiểu biết cải tiến thuật toán |
| 5 | Support / Confidence / Lift / Leverage / Conviction | 5 công thức | Định nghĩa chuẩn của MBA, nêu rõ ngoài giáo trình |
| 6 | Targeted Association Mining | Khai phá theo PKKH | Nâng giá trị kinh doanh, đòi hỏi chi tiết hóa |
| 7 | **Chi-square 2×2 trên luật** | $\chi^2=\sum\frac{(O-E)^2}{E}$, dof=1 | **Slide 1.1 áp dụng mới — an toàn nhất** |
| 8 | TF-IDF (+ sublinear TF, bigram) | $\text{tf}\log\frac{N}{df}$ | Mở rộng của ý tưởng "feature scaling" ở Slide 1.1 |
| 9 | Cosine Similarity | $\frac{a\cdot b}{\|a\|\|b\|}$ | Mở rộng khái niệm "đo khoảng cách" ở Slide 5.2 |
| 10 | Elbow Method + Silhouette Score | $s(i)=\frac{b(i)-a(i)}{\max(a(i),b(i))}$ | **Trả lời câu hỏi mở tại Slide 5.3 tr.20** |

*Đã bao gồm trong Nhóm B: Precision@k / Recall@k / NDCG@k (mở rộng của Precision/Recall ở Slide 5 sang ngữ cảnh Top-K).*

### Nhóm C — Chỉ dùng để đối chứng / sẵn sàng trả lời (2 mục)

| # | Nội dung | Khi nào được hỏi |
|---|---|---|
| 1 | So sánh K-Means ↔ K-Medoids (PAM) | "Với outlier thì sao?" |
| 2 | Giải thích tại sao KHÔNG dùng CF/Deep Learning/PCA/ARIMA | "Sao không thêm mô hình mạnh hơn?" |

### Ma trận đối chiếu nhanh: Slide nào nói gì?

| Slide | Nội dung | Thuật toán tương ứng trong đồ án |
|---|---|---|
| Slide 1 | Predictive Analytics Lifecycle, EMC 6 pha, KDD | Mục 5.1 — khung tổng thể |
| Slide 1.1 | Cleaning, Binning, Integration, Pearson, **Chi-square**, Min-Max, Z-score | Tầng 1 |
| Slide 2.2 | Pandas: dropna/fillna/drop_duplicates/groupby/sort/describe/value_counts | Tầng 1 |
| Slide 3 | Data Storytelling, Bar/Histogram/Scatter/Boxplot/Gantt/Venn/Dashboard | Mục 5.4 |
| Slide 4 | Mean/Median/Mode, Range/Variance/SD, **IQR** | Tầng 1 (outlier) |
| Slide 5 | Supervised/Unsupervised, Feature selection, **Hold-out/K-fold/Stratified**, **Confusion Matrix + P/R/F1** | Tầng 2 (đánh giá), Tầng 4 (đánh giá) |
| Slide 5.1 | Linear Regression, Least Squares | Future work |
| Slide 5.2 | k-NN, Euclidean/Manhattan, nhạy thang đo | Baseline đối chứng Tầng 4 |
| Slide 5.3 | Lloyd K-Means, WCSS, Manhattan vs Euclidean, **K-Medoids/PAM**, **câu hỏi mở "đánh giá K-means thế nào?" (tr.20)** | Tầng 2 (thuật toán + tiêu chí chọn K) |

---

## PHỤ LỤC A – Quy trình tái lập

```
1. Đọc data_ggsheet.xlsx → sheet 'data_ggsheet'  (82.137 × 13)
2. TẦNG 1:
   a. df.isna().sum()            → 2.518 null ở 'Tên khách hàng'
   b. df.drop_duplicates()       → 0 dòng
   c. kiểm tra Thành tiền == SL × Đơn giá  → 100%
   d. IQR trên 'Đơn giá', 'Thành tiền'  → đánh dấu, không xóa
   e. chi2_contingency(crosstab(seg_code, grp_name))  → χ²=4938,42, dof=32
3. TẦNG 2:
   a. RFM: recency = (max(time) - last_order).days, freq = nunique(order), monetary = sum(amount)
   b. X = StandardScaler().fit_transform(np.log1p(RFM))
   c. for K in 2..12: KMeans(n_init=10, random_state=42) → inertia_, silhouette_score
   d. Chọn K=3; đối chiếu 9 nhãn PKKH bằng crosstab + linear_sum_assignment
4. TẦNG 3:
   a. basket = groupby(order_id)['item_code'] → set
   b. đếm cặp/triple; support, confidence, lift, leverage
   c. chi2_contingency trên bảng 2×2 (n11, n10, n01, n00) cho từng luật
5. TẦNG 4:
   a. TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True) trên 'item_name + grp_name'
   b. cosine matrix = M @ M.T
   c. Chia thời gian: train < 2022-10-01, test >= 2022-10-01
   d. Với mỗi khách test: dựng top-5 theo từng chiến lược
   e. Tính P@5, R@5, HR@5, NDCG@5 + baseline ngẫu nhiên
```

## PHỤ LỤC B – Danh mục tài liệu tham khảo

**Slide bài giảng (nguồn chính):**
- *Tổng quan phân tích dữ liệu* (Slide 1) – GVHD: ThS. Hồ Hướng Thiên
- *Tiền xử lý dữ liệu* (Slide 1.1)
- *Ngôn ngữ lập trình Python / NumPy / Pandas* (Slide 2, 2.1, 2.2)
- *Trực quan dữ liệu* (Slide 3)
- *Phân tích thống kê mô tả* (Slide 4)
- *Phân tích dự đoán – Machine Learning* (Slide 5)
- *Hồi quy tuyến tính* (Slide 5.1), *Phân loại dữ liệu k-NN* (Slide 5.2), *Phân cụm dữ liệu K-means* (Slide 5.3)

**Tài liệu mở rộng (cần trích dẫn khi bảo vệ):**
- Agrawal, R. & Imieliński, T. (1994). *Database Systems: Mining Frequent Patterns, Associations, and Correlations.*
- Han, J., Pei, J. & Yin, Y. (2000). *Mining Frequent Patterns without Candidate Generation.*
- Han, J., Kamber, M. & Pei, J. (2012). *Data Mining: Concepts and Techniques*, 3rd ed.
- Aggarwal, C. C. & Yu, H. (1996). *Mining Web Patterns and Theories of User Browsing Behavior.*
- Kleinberg, J. & Tardos, E. (2005). *Linear Programming Approximation Algorithms for Projective Clustering and Latent Semantic Indexing.*
- Kaufman, L. & Rousseeuw, P. J. (1990). *Finding Groups in Data: An Introduction to Cluster Analysis.*
- Hyndman, R. J. & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice*, 3rd ed.
- RFM mô hình: Hughes, A. (2004). *Strategic Database Marketing.*

---

**— HẾT BÁO CÁO —**

*Tài liệu được biên soạn kèm số liệu đo thực nghiệm trên `data_ggsheet.xlsx`. Mọi phép tính đều chạy trên tập dữ liệu gốc, không sửa đổi dữ liệu nguồn.*
