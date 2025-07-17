import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, items_db, Item
import os
import time

# Initialize TestClient for FastAPI application
client = TestClient(app)

# Fixture to clear and reset the in-memory database for each test
@pytest.fixture(autouse=True)
def reset_db():
    """
    Resets the in-memory database before each test to ensure test isolation.
    In a real application, this would involve connecting to a test database
    and clearing/repopulating it.
    """
    original_items_db = items_db.copy()
    items_db.clear()
    items_db.update({
        1: Item(id=1, name="Initial Item 1", description="Description for initial item 1"),
        2: Item(id=2, name="Initial Item 2", description="Description for initial item 2"),
    })
    yield # Run the test
    items_db.clear()
    items_db.update(original_items_db) # Restore original state if needed, or just clear

def test_integration_health_check():
    """
    Integration test for the health check endpoint.
    Verifies the endpoint is accessible and returns the correct status.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_integration_read_items():
    """
    Integration test for reading all items.
    Verifies that the endpoint returns the expected initial items.
    """
    response = client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(item["name"] == "Initial Item 1" for item in data)
    assert any(item["name"] == "Initial Item 2" for item in data)

def test_integration_read_single_item():
    """
    Integration test for reading a single item by ID.
    Verifies correct item retrieval and 404 for non-existent items.
    """
    # Test existing item
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Initial Item 1"

    # Test non-existent item
    response = client.get("/items/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"

# Example of a more complex integration test involving multiple endpoints or state changes
# (Though for a simple GET API, this might be overkill)
def test_integration_create_and_read_item():
    """
    Simulates a create operation (if available) and then reads the created item.
    This test would require a POST endpoint for creating items.
    For this example, we'll simulate adding to the in-memory DB and then reading.
    """
    new_item_data = {"id": 3, "name": "New Test Item", "description": "Created during integration test"}

    # Simulate adding an item (if there was a POST /items endpoint)
    # For now, directly add to the in-memory DB for demonstration
    items_db[new_item_data["id"]] = Item(**new_item_data)

    # Now, try to read all items and verify the new item is present
    response_all = client.get("/items")
    assert response_all.status_code == 200
    data_all = response_all.json()
    assert len(data_all) == 3 # Initial 2 + 1 new
    assert any(item["name"] == "New Test Item" for item in data_all)

    # Try to read the specific new item
    response_new = client.get(f"/items/{new_item_data['id']}")
    assert response_new.status_code == 200
    assert response_new.json()["name"] == "New Test Item"
    assert response_new.json()["description"] == "Created during integration test"

# Example of testing environment variable loading (if applicable to integration)
def test_integration_cors_origins_from_env():
    """
    Tests if CORS origins are correctly loaded from environment variables.
    This is an integration test as it involves the FastAPI app's startup configuration.
    """
    # Temporarily set an environment variable for the test
    os.environ["CORS_ORIGINS"] = "http://test-origin.com"
    # Re-initialize the app to pick up the new env var (not ideal for every test, but for this specific check)
    # In a real scenario, you might restart the test client or use a fixture that sets env vars before app init.
    from importlib import reload
    import backend.app.main
    reload(backend.app.main)
    test_client_with_env = TestClient(backend.app.main.app)

    response = test_client_with_env.options("/", headers={"Origin": "http://test-origin.com", "Access-Control-Request-Method": "GET"})
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://test-origin.com"

    response_invalid = test_client_with_env.options("/", headers={"Origin": "http://invalid-origin.com", "Access-Control-Request-Method": "GET"})
    # Depending on CORS configuration, this might be 200 but without the header, or 400/403
    # FastAPI's default behavior for disallowed origin is to not include the header.
    assert "access-control-allow-origin" not in response_invalid.headers

    # Clean up the environment variable
    del os.environ["CORS_ORIGINS"]
    # Reload app again to revert to original state
    reload(backend.app.main)