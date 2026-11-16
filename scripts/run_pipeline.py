#!/usr/bin/env python
"""Chạy toàn bộ pipeline 4 tầng và sinh báo cáo + biểu đồ.

Usage::

    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --data /path/to/data.xlsx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_pipeline, save_artifacts  # noqa: E402
from src.reporting.charts import generate_all_charts  # noqa: E402
from src.reporting.report import build_markdown_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Hệ thống phân tích giỏ hàng & gợi ý đa tầng")
    parser.add_argument("--data", default=None, help="Đường dẫn file dữ liệu (mặc định: data_ggsheet.xlsx)")
    parser.add_argument("--no-charts", action="store_true", help="Bỏ qua việc sinh biểu đồ")
    parser.add_argument("--no-report", action="store_true", help="Bỏ qua việc sinh báo cáo Markdown")
    args = parser.parse_args()

    result = run_pipeline(data_path=args.data)

    print("\n[8/9] Lưu artifact...")
    paths = save_artifacts(result)
    for name, path in paths.items():
        print(f"      {name:18s} → {path}")

    if not args.no_charts:
        print("\n[9/9] Sinh biểu đồ...")
        charts = generate_all_charts(result)
        for path in charts:
            print(f"      → {Path(path).name}")

    if not args.no_report:
        print("\nSinh báo cáo Markdown...")
        report = build_markdown_report(result)
        print(f"      → {report}")

    print("\n✅ Hoàn tất.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
