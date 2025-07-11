import pytest
import httpx
import os
import time

# Base URL for the FastAPI application, assuming it's running on localhost:8000
# This will be used when running tests against a live Docker container
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

@pytest.fixture(scope="module", autouse=True)
def wait_for_api():
    """Waits for the API to be available before running tests."""
    print(f"Waiting for API at {BASE_URL} to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            response = httpx.get(f"{BASE_URL}/health", timeout=1)
            if response.status_code == 200 and response.json().get("status") == "ok":
                print("API is ready!")
                return
        except httpx.RequestError as e:
            print(f"API not ready yet: {e}. Retrying in 2 seconds...")
        time.sleep(2)
    pytest.fail(f"API did not become available at {BASE_URL} after {max_retries * 2} seconds.")

def test_integration_read_root():
    response = httpx.get(f"{BASE_URL}/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI Monitoring Demo!"}

def test_integration_health_check():
    response = httpx.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_integration_read_item():
    response = httpx.get(f"{BASE_URL}/items/10")
    assert response.status_code == 200
    assert response.json() == {"item_id": 10, "name": "Item 10"}

def test_integration_create_item():
    payload = {"name": "Integration Test Item", "description": "Created via integration test"}
    response = httpx.post(f"{BASE_URL}/items/", json=payload)
    assert response.status_code == 201
    assert response.json()["name"] == "Integration Test Item"

def test_integration_metrics_endpoint():
    response = httpx.get(f"{BASE_URL}/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text
    assert "app_info" in response.text # Check for custom app metric