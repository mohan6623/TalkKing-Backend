"""Tests for FastAPI app factory and health endpoint."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    """GET /health should return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "talkking-api"


def test_health_includes_environment():
    """Health response should include the current environment."""
    response = client.get("/health")
    body = response.json()
    assert "env" in body
    assert body["env"] == "development"


def test_api_docs_accessible():
    """OpenAPI docs should be served at /api/docs."""
    response = client.get("/api/docs")
    assert response.status_code == 200


def test_api_redoc_accessible():
    """Redoc should be served at /api/redoc."""
    response = client.get("/api/redoc")
    assert response.status_code == 200


def test_cors_headers():
    """Preflight CORS request should include proper headers."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
