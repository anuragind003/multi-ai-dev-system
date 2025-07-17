import pytest
import httpx
import os
import time

# Assuming the Docker container is running on localhost:8000
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

@pytest.fixture(scope="module", autouse=True)
def wait_for_api():
    """Waits for the API to be available before running tests."""
    max_retries = 10
    retry_delay = 2 # seconds
    for i in range(max_retries):
        try:
            response = httpx.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print(f"API is ready after {i*retry_delay} seconds.")
                return
        except httpx.RequestError:
            pass
        print(f"Waiting for API... (Attempt {i+1}/{max_retries})")
        time.sleep(retry_delay)
    pytest.fail(f"API did not become available at {BASE_URL} after {max_retries} attempts.")


def test_integration_health_check():
    response = httpx.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Service is healthy"}

def test_integration_read_root():
    response = httpx.get(f"{BASE_URL}/")
    assert response.status_code == 200
    assert "Welcome to the FastAPI Production Service!" in response.json()["message"]

def test_integration_create_and_read_item():
    item_data = {"name": "Integration Test Item", "description": "Created via integration test", "price": 99.99}
    post_response = httpx.post(f"{BASE_URL}/items/", json=item_data)
    assert post_response.status_code == 201
    created_item = post_response.json()
    assert created_item["name"] == "Integration Test Item"

    # Assuming the API returns a consistent ID or we can query by name
    # For this simple example, we'll just test a known ID
    get_response = httpx.get(f"{BASE_URL}/items/4") # Assuming ID 4 exists or is created
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Item 4"

def test_integration_get_config():
    response = httpx.get(f"{BASE_URL}/config")
    assert response.status_code == 200
    # This will reflect the actual environment variable set in the Docker container
    assert response.json()["my_secret_key"] == "dev_secret_key_123" # From docker-compose.yml