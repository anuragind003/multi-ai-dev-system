import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_main_health():
    """
    Test the /health endpoint.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "message": "Service is up and running!"}

def test_read_metrics_endpoint():
    """
    Test the /metrics endpoint returns Prometheus format.
    """
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds_bucket" in response.text
    assert "app_info" in response.text
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"

def test_read_item():
    """
    Test the /items/{item_id} endpoint.
    """
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json() == {"item_id": 1, "name": "Item 1"}

def test_read_item_not_found():
    """
    Test the /items/{item_id} endpoint for a 404 case.
    """
    response = client.get("/items/404")
    assert response.status_code == 404
    assert response.json() == {"message": "Item not found"}

def test_read_item_internal_server_error():
    """
    Test the /items/{item_id} endpoint for a 500 case.
    """
    response = client.get("/items/500")
    assert response.status_code == 500
    assert response.json() == {"message": "Simulated Internal Server Error"}