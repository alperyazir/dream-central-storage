from fastapi.testclient import TestClient

from app.main import app


def test_storage_health_endpoint():
    client = TestClient(app)
    resp = client.get("/storage/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data and data["status"] in {"ok", "error"}
    assert "detail" in data
