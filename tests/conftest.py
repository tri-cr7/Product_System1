"""Pytest fixtures dùng chung cho toàn bộ test."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.loader import load_transactions  # noqa: E402


@pytest.fixture(scope="session")
def raw_df():
    """Bộ dữ liệu thô đã nạp từ Excel (session scope để chỉ đọc 1 lần)."""
    return load_transactions().frame


@pytest.fixture(scope="session")
def small_df(raw_df):
    """Mẫu nhỏ (5.000 dòng) để test chạy nhanh."""
    return raw_df.head(5000).copy()
