from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_health_status():
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "ok",
        "service": app.title,
        "version": app.version,
    }


def test_explicit_health_endpoint_matches_root():
    root_response = client.get("/")
    health_response = client.get("/health")

    assert root_response.status_code == 200
    assert health_response.status_code == 200
    assert root_response.json() == health_response.json()
