from fastapi.testclient import TestClient

from noahsark.config import settings
from noahsark.main import app

client = TestClient(app)

def test_healthz_ok():
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] in {"configured", "not_configured"}

def test_readyz_fails_closed_without_database(monkeypatch):
    monkeypatch.setattr(settings, "database_url", None)
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"

def test_openapi_available():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "NoahsArk Control Plane"
