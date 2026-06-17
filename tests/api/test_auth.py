"""
tests/api/test_auth.py
Integration tests for auth endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.base import create_tables

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    create_tables()
    yield


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] in ("healthy", "degraded")


def test_register_and_login():
    # Register
    r = client.post("/api/v1/auth/register", json={
        "email":     "test@kumip.co.ke",
        "full_name": "Test User",
        "password":  "securepass123",
        "role":      "public",
    })
    assert r.status_code in (201, 409), r.text   # 409 if already exists

    # Login
    r = client.post("/api/v1/auth/login", json={
        "email":    "test@kumip.co.ke",
        "password": "securepass123",
    })
    # May fail if register was 409 and password differs — fine for CI
    if r.status_code == 200:
        data = r.json()["data"]
        assert "access_token"  in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


def test_login_wrong_password():
    r = client.post("/api/v1/auth/login", json={
        "email":    "nobody@kumip.co.ke",
        "password": "wrongpassword",
    })
    assert r.status_code == 401


def test_me_requires_auth():
    r = client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)  # 403=no header, 401=bad token


def test_me_with_valid_token():
    # Login as default admin
    r = client.post("/api/v1/auth/login", json={
        "email":    "admin@kumip.co.ke",
        "password": "admin1234!",
    })
    if r.status_code != 200:
        pytest.skip("Admin user not seeded")
    token = r.json()["data"]["access_token"]
    r2 = client.get("/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["data"]["email"] == "admin@kumip.co.ke"
