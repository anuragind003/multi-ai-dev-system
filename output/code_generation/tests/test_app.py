import pytest
from fastapi.testclient import TestClient
from app.main import app # Assuming app/main.py is the entry point

# Initialize TestClient
client = TestClient(app)

def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FastAPI Sentry Demo!"}

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "version" in response.json()

def test_trigger_error():
    """
    Test the error triggering endpoint.
    This should result in a 500 Internal Server Error.
    Sentry should capture this error.
    """
    response = client.get("/error")
    assert response.status_code == 500
    assert response.json() == {"message": "An unexpected error occurred."}

def test_metrics_endpoint():
    """Test the Prometheus metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds_bucket" in response.text

def test_app_info_endpoint():
    """Test the application information endpoint."""
    response = client.get("/info")
    assert response.status_code == 200
    assert "app_name" in response.json()
    assert "app_version" in response.json()
    assert "environment" in response.json()
    assert "sentry_enabled" in response.json()
    assert "log_level" in response.json()