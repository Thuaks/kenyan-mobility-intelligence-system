"""
tests/api/test_routes_api.py
Tests for route, accident, demand, and social endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_admin_token() -> str | None:
    r = client.post("/api/v1/auth/login", json={
        "email": "admin@kumip.co.ke", "password": "admin1234!"
    })
    if r.status_code == 200:
        return r.json()["data"]["access_token"]
    return None


def auth_headers() -> dict:
    token = get_admin_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


# ── Route endpoints ───────────────────────────────────────────────────────────
def test_list_routes_no_auth():
    """Routes listing should be public."""
    r = client.get("/api/v1/routes/")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True


def test_accident_stats():
    r = client.get("/api/v1/accidents/stats")
    assert r.status_code == 200


def test_blackspots():
    r = client.get("/api/v1/accidents/blackspots?min_incidents=2")
    assert r.status_code == 200
    body = r.json()
    assert "blackspots" in body["data"]


def test_heatmap_data():
    r = client.get("/api/v1/accidents/heatmap-data")
    assert r.status_code == 200


def test_demand_summary():
    r = client.get("/api/v1/demand/summary")
    assert r.status_code == 200


def test_social_sentiment():
    r = client.get("/api/v1/social/sentiment")
    assert r.status_code == 200
    body = r.json()
    assert "totals" in body["data"]


def test_social_incidents():
    r = client.get("/api/v1/social/incidents?limit=10")
    assert r.status_code == 200


def test_admin_requires_auth():
    r = client.get("/api/v1/admin/users")
    assert r.status_code in (401, 403)


def test_admin_users_with_token():
    headers = auth_headers()
    if not headers:
        pytest.skip("Admin token unavailable")
    r = client.get("/api/v1/admin/users", headers=headers)
    assert r.status_code == 200


def test_system_stats():
    headers = auth_headers()
    if not headers:
        pytest.skip("Admin token unavailable")
    r = client.get("/api/v1/admin/system/stats", headers=headers)
    assert r.status_code == 200
    assert "record_counts" in r.json()["data"]
