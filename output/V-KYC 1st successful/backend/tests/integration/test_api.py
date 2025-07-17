import pytest
import httpx
import os
import time

# Base URL for the API, typically the service exposed by Docker Compose or Kubernetes
# For integration tests, we assume the service is running and accessible.
# In CI, this might be 'http://localhost:8000' if running in a container,
# or a specific service name if running within a Docker network.
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

@pytest.fixture(scope="module")
def api_client():
    """
    Fixture to provide an HTTP client for API requests.
    Ensures the service is up before tests run.
    """
    # Wait for the service to be ready
    max_retries = 10
    for i in range(max_retries):
        try:
            response = httpx.get(f"{API_BASE_URL}/health")
            response.raise_for_status()
            print(f"Service is healthy: {response.json()}")
            break
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"Service not ready yet (attempt {i+1}/{max_retries}): {e}")
            time.sleep(2)
    else:
        pytest.fail(f"Service did not become ready after {max_retries * 2} seconds.")

    return httpx.Client(base_url=API_BASE_URL)

def test_integration_root_endpoint(api_client: httpx.Client):
    """
    Integration test for the root endpoint.
    Verifies connectivity and basic response from the running service.
    """
    response = api_client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "Welcome to the FastAPI Backend!"

def test_integration_health_check_endpoint(api_client: httpx.Client):
    """
    Integration test for the health check endpoint.
    """
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_integration_create_and_get_item(api_client: httpx.Client):
    """
    Integration test for creating an item and then retrieving it.
    This tests the full API flow.
    """
    # 1. Create an item
    item_data = {
        "name": "Integration Test Item",
        "description": "Item created during integration test",
        "price": 25.50,
        "tax": 2.50
    }
    create_response = api_client.post("/items/", json=item_data)
    assert create_response.status_code == 201
    created_item = create_response.json()
    assert created_item["name"] == item_data["name"]
    assert created_item["price"] == item_data["price"]

    # 2. Try to get the item (assuming a simple ID mechanism or known ID)
    # Note: Our current app.main.py only returns a hardcoded item for ID 1.
    # For a real app, you'd get the ID from the create_response and use it.
    # For this example, we'll just test the hardcoded ID 1.
    get_response = api_client.get("/items/1")
    assert get_response.status_code == 200
    retrieved_item = get_response.json()
    assert retrieved_item["name"] == "Sample Item" # This is from the hardcoded logic in main.py
    assert retrieved_item["price"] == 10.99

def test_integration_get_non_existent_item(api_client: httpx.Client):
    """
    Integration test for retrieving a non-existent item.
    """
    response = api_client.get("/items/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"

# Add more integration tests as needed to cover critical API flows.