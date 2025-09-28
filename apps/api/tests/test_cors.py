"""Tests validating API CORS configuration."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_preflight_succeeds_for_allowed_origin() -> None:
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_preflight_is_rejected_for_disallowed_origin() -> None:
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://malicious.local",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
