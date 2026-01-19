from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "commit" in body

def test_metrics_available():
    r = client.get("/metrics")
    assert r.status_code == 200
    text = r.text
    assert "http_requests_total" in text
    assert "http_request_duration_seconds" in text
    assert "build_info" in text
