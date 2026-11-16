"""Test API FastAPI (dùng TestClient)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_root_endpoint():
    r = client.get("/")
    assert r.status_code == 200
    assert "endpoints" in r.json()


def test_health_endpoint():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] in {"ok", "no-artifacts"}


@pytest.mark.skipif(
    not __import__("pathlib").Path(__file__).resolve().parent.parent.joinpath(
        "output/artifacts/summary.json"
    ).exists(),
    reason="Cần chạy pipeline trước",
)
def test_summary_endpoint():
    r = client.get("/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["n_rows"] > 0
    assert "clustering" in data


@pytest.mark.skipif(
    not __import__("pathlib").Path(__file__).resolve().parent.parent.joinpath(
        "output/artifacts/summary.json"
    ).exists(),
    reason="Cần chạy pipeline trước",
)
def test_customers_endpoint():
    r = client.get("/customers", params={"limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) <= 5
    assert "total" in data


@pytest.mark.skipif(
    not __import__("pathlib").Path(__file__).resolve().parent.parent.joinpath(
        "output/artifacts/summary.json"
    ).exists(),
    reason="Cần chạy pipeline trước",
)
def test_recommendations_endpoint():
    r = client.get("/customers", params={"limit": 1})
    cid = r.json()["items"][0]["customer_id"]
    rr = client.get(f"/customers/{cid}/recommendations")
    assert rr.status_code == 200
    data = rr.json()
    assert data["customer_id"] == cid
    assert len(data["recommendations"]) <= 5
    assert data["branch_used"] in {"A", "B"}


@pytest.mark.skipif(
    not __import__("pathlib").Path(__file__).resolve().parent.parent.joinpath(
        "output/artifacts/summary.json"
    ).exists(),
    reason="Cần chạy pipeline trước",
)
def test_clusters_and_rules():
    assert client.get("/clusters").status_code == 200
    assert client.get("/rules", params={"limit": 5}).status_code == 200
    assert client.get("/evaluation").status_code == 200


def test_unknown_customer_returns_404():
    r = client.get("/customers/khong_ton_tai_xyz/recommendations")
    assert r.status_code in {404, 503}
