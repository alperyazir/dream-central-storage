from __future__ import annotations

import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _add_protected_route(app: FastAPI) -> None:
    @app.get("/private")
    def private():  # type: ignore[return-type]
        return {"ok": True}


def _reload_app():
    import app.main as main_mod

    importlib.reload(main_mod)
    return main_mod.app


def test_public_paths_bypass_auth():
    app = _reload_app()
    client = TestClient(app)
    for path in ("/health", "/storage/health"):
        resp = client.get(path)
        assert resp.status_code == 200


def test_missing_authorization_header_returns_401(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_BEARER_TOKEN", "secret-token")
    app = _reload_app()
    _add_protected_route(app)
    client = TestClient(app)
    resp = client.get("/private")
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate", "").lower() == "bearer"


def test_non_bearer_scheme_returns_401(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_BEARER_TOKEN", "secret-token")
    app = _reload_app()
    _add_protected_route(app)
    client = TestClient(app)
    resp = client.get("/private", headers={"Authorization": "Basic abc"})
    assert resp.status_code == 401


def test_empty_bearer_token_returns_401(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_BEARER_TOKEN", "secret-token")
    app = _reload_app()
    _add_protected_route(app)
    client = TestClient(app)
    resp = client.get("/private", headers={"Authorization": "Bearer "})
    assert resp.status_code == 401


def test_wrong_token_returns_403(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_BEARER_TOKEN", "secret-token")
    app = _reload_app()
    _add_protected_route(app)
    client = TestClient(app)
    resp = client.get("/private", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 403


def test_correct_token_allows_access(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_BEARER_TOKEN", "secret-token")
    app = _reload_app()
    _add_protected_route(app)
    client = TestClient(app)
    resp = client.get("/private", headers={"Authorization": "Bearer secret-token"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
