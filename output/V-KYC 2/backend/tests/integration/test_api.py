import pytest
import httpx
import os
import time

# Determine the base URL for the API.
# In CI/CD, this might be a Docker service name.
# For local testing, it could be localhost.
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# A simple retry mechanism for integration tests,
# especially useful when services are starting up in Docker Compose.
def retry(attempts=5, delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for i in range(attempts):
                try:
                    return func(*args, **kwargs)
                except httpx.RequestError as e:
                    print(f"Attempt {i+1}/{attempts} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
            raise Exception(f"Failed after {attempts} attempts.")
        return wrapper
    return decorator

@pytest.fixture(scope="module")
@retry(attempts=10, delay=2) # Give services time to start
def client():
    """Provides an httpx client for API calls."""
    print(f"Connecting to API at: {API_BASE_URL}")
    with httpx.Client(base_url=API_BASE_URL) as client:
        # Verify health check before proceeding with tests
        response = client.get("/health")
        response.raise_for_status() # Raise an exception for bad status codes
        assert response.json()["status"] == "ok"
        yield client

def test_integration_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI Monorepo Backend!"}

def test_integration_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_integration_create_data(client):
    data = {"name": "Integration Test Data", "value": 12345}
    response = client.post("/data", json=data)
    assert response.status_code == 201
    assert response.json()["message"] == "Data received"
    assert response.json()["data"] == data

def test_integration_read_item_unauthorized(client):
    response = client.get("/items/999")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_integration_read_item_authorized(client):
    # Use the known test token from backend/app/main.py
    headers = {"Authorization": "Bearer supersecrettoken"}
    response = client.get("/items/100?q=integration", headers=headers)
    assert response.status_code == 200
    assert response.json()["item_id"] == 100
    assert response.json()["q"] == "integration"
    assert response.json()["user"]["username"] == "testuser"

def test_integration_metrics_endpoint(client):
    # This assumes Prometheus middleware is enabled and exposes /metrics
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text