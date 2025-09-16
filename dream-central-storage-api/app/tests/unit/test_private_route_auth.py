from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


def _reload_app():
    import app.main as main_mod

    importlib.reload(main_mod)
    return main_mod.app


def test_private_route_requires_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AUTH_BEARER_TOKEN", raising=False)
    app = _reload_app()
    client = TestClient(app)
    resp = client.get("/api/v1/private/ping")
    # With no configured token, any provided token is accepted; but with none provided → 401
    assert resp.status_code == 401


def test_private_route_authorized_with_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_BEARER_TOKEN", "secret-token")
    app = _reload_app()
    client = TestClient(app)
    # No header → 401
    resp = client.get("/api/v1/private/ping")
    assert resp.status_code == 401
    # Wrong token → 403
    resp2 = client.get("/api/v1/private/ping", headers={"Authorization": "Bearer wrong"})
    assert resp2.status_code == 403
    # Correct token → 200
    resp3 = client.get("/api/v1/private/ping", headers={"Authorization": "Bearer secret-token"})
    assert resp3.status_code == 200
    assert resp3.json() == {"status": "ok"}
