# Hệ thống Phân tích Giỏ Hàng & Gợi ý Sản Phẩm Đa Tầng
# Dùng: make <mục tiêu>   — xem `make help` để biết tất cả mục tiêu

PY := .venv/bin/python
PIP := .venv/bin/pip
PORT_API := 8000
PORT_DASH := 8501

# Tắt warning nhiễu: matplotlib cần thư mục cache ghi được;
# joblib cần biết số core để không cảnh báo trên macOS.
export MPLCONFIGDIR := $(CURDIR)/.cache/matplotlib
export LOKY_MAX_CPU_COUNT := 4
export PYTHONWARNINGS := ignore::UserWarning

.DEFAULT_GOAL := help
.PHONY: help setup install pipeline test api dashboard tune clean clean-output lint all

## ── Trợ giúp ───────────────────────────────────────────────────────────────
help: ## Hiển thị danh sách lệnh
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║  HỆ THỐNG PHÂN TÍCH GIỎ HÀNG & GỢI Ý SẢN PHẨM ĐA TẦNG      ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  make setup        Tạo môi trường ảo & cài thư viện (chạy 1 lần)"
	@echo "  make pipeline     Chạy toàn bộ hệ thống 4 tầng + sinh biểu đồ + báo cáo"
	@echo "  make test         Chạy test suite (77 test)"
	@echo "  make api          Khởi động REST API  → http://localhost:$(PORT_API)/docs"
	@echo "  make dashboard    Khởi động Streamlit   → http://localhost:$(PORT_DASH)"
	@echo "  make tune         Sweep trọng số gộp tín hiệu (tối ưu P@5/NDCG@5)"
	@echo "  make clean-output Xóa kết quả sinh ra (artifacts/charts/report)"
	@echo "  make clean        Xóa cả cache Python + kết quả sinh ra"
	@echo "  make all          pipeline + test + báo cáo (dùng trước khi nộp)"
	@echo ""

## ── Cài đặt ───────────────────────────────────────────────────────────────
setup: ## Tạo venv + cài thư viện
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@mkdir -p .cache/matplotlib
	@echo ""
	@echo "✅ Hoàn tất. Chạy tiếp:  make pipeline"

install: ## Cài lại thư viện trong venv hiện có
	$(PIP) install -r requirements.txt

## ── Chạy hệ thống ─────────────────────────────────────────────────────────
pipeline: ## Chạy pipeline 4 tầng + biểu đồ + báo cáo
	$(PY) scripts/run_pipeline.py

test: ## Chạy test suite
	$(PY) -m pytest

lint: ## Kiểm tra cú pháp toàn bộ mã nguồn
	$(PY) -m compileall -q src dashboard scripts tests && echo "✅ Cú pháp hợp lệ"

tune: ## Sweep trọng số gộp tín hiệu
	$(PY) scripts/tune_weights.py

api: ## Chạy REST API (FastAPI + Swagger UI)
	$(PY) -m uvicorn src.api.main:app --reload --port $(PORT_API)

dashboard: ## Chạy dashboard (Streamlit)
	$(PY) -m streamlit run dashboard/app.py --server.port $(PORT_DASH)

all: pipeline test ## Chạy pipeline + test + báo cáo

## ── Dọn dẹp ───────────────────────────────────────────────────────────────
clean-output: ## Xóa kết quả sinh ra
	rm -rf output/artifacts output/charts output/report
	find . -name "__pycache__" -type d -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
	@echo "✅ Đã xóa kết quả sinh ra"

clean: clean-output ## Xóa cache + kết quả
	@echo "✅ Đã dọn sạch"
