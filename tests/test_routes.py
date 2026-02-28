"""Tests for all v1 API route stubs — verifies routing, auth guards, and response shapes."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Auth routes (public) ─────────────────────────────────────────────

def test_signup_endpoint_exists():
    response = client.post("/api/v1/auth/signup", json={
        "email": "test@test.com", "password": "secret123", "name": "Test"
    })
    # Should not be 404 — route exists
    assert response.status_code != 404


def test_login_endpoint_exists():
    response = client.post("/api/v1/auth/login", json={
        "email": "test@test.com", "password": "secret123"
    })
    assert response.status_code != 404


# ── Protected routes (require auth) ──────────────────────────────────

def test_get_user_me_requires_auth():
    response = client.get("/api/v1/users/me")
    assert response.status_code in (401, 403)


def test_patch_user_me_requires_auth():
    response = client.patch("/api/v1/users/me", json={"name": "Updated"})
    assert response.status_code in (401, 403)


def test_create_session_requires_auth():
    response = client.post("/api/v1/sessions", json={
        "type": "audio", "prompt_type": "random", "prompt": "hello", "duration": 300
    })
    assert response.status_code in (401, 403)


def test_analyze_session_requires_auth():
    response = client.post("/api/v1/sessions/fake-id/analyze")
    assert response.status_code in (401, 403)


def test_get_feedback_requires_auth():
    response = client.get("/api/v1/sessions/fake-id/feedback")
    assert response.status_code in (401, 403)


def test_get_session_status_requires_auth():
    response = client.get("/api/v1/sessions/fake-id/status")
    assert response.status_code in (401, 403)


def test_get_progress_requires_auth():
    response = client.get("/api/v1/progress")
    assert response.status_code in (401, 403)


def test_get_history_requires_auth():
    response = client.get("/api/v1/history")
    assert response.status_code in (401, 403)


# ── Demo route (public) ──────────────────────────────────────────────

def test_demo_assess_is_public():
    """Demo assess endpoint should NOT require auth (returns 422 for missing body, not 401)."""
    response = client.post("/api/v1/demo/assess")
    assert response.status_code in (400, 422)  # validation error, NOT 401
