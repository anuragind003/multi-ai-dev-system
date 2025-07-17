from fastapi.testclient import TestClient
from app.main import app

# Using the client fixture from conftest.py
def test_read_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to the FastAPI Portal!" in response.text

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "FastAPI Portal is healthy"}

def test_readiness_probe_success(client: TestClient):
    # Assuming readiness probe passes by default in test environment
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["dependencies"]["database"] == "ok"

def test_read_item_success(client: TestClient):
    item_id = 1
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 200
    assert response.json() == {"item_id": item_id, "name": f"Item {item_id}"}

def test_read_item_not_found(client: TestClient):
    item_id = 0 # Our mock logic returns 404 for item_id 0
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}

def test_openapi_spec_exists(client: TestClient):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "title" in response.json()
    assert "version" in response.json()
    assert "paths" in response.json()

def test_metrics_endpoint_exists(client: TestClient):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds_bucket" in response.text