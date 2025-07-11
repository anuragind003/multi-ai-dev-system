import pytest
from unittest.mock import MagicMock, patch
from backend.app.main import app, Item, items_db
from fastapi.testclient import TestClient

# Initialize TestClient for FastAPI application
client = TestClient(app)

def test_health_check_unit():
    """
    Unit test for the health check endpoint.
    Ensures the endpoint returns the correct status and message.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Backend service is healthy!"}

def test_read_item_existing_unit():
    """
    Unit test for reading an existing item.
    Mocks the database interaction to ensure isolation.
    """
    # Mock the items_db to control test data
    with patch('backend.app.main.items_db', {1: Item(id=1, name="Test Item", description="Test Description")}):
        response = client.get("/items/1")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "Test Item", "description": "Test Description"}

def test_read_item_not_found_unit():
    """
    Unit test for reading a non-existent item.
    Mocks the database interaction.
    """
    with patch('backend.app.main.items_db', {}): # Empty database
        response = client.get("/items/999")
        assert response.status_code == 404
        assert response.json() == {"detail": "Item not found"}

def test_read_items_unit():
    """
    Unit test for reading all items.
    Mocks the database interaction.
    """
    mock_items = {
        1: Item(id=1, name="Item A"),
        2: Item(id=2, name="Item B")
    }
    with patch('backend.app.main.items_db', mock_items):
        response = client.get("/items")
        assert response.status_code == 200
        assert response.json() == [
            {"id": 1, "name": "Item A", "description": None},
            {"id": 2, "name": "Item B", "description": None}
        ]

def test_root_endpoint_unit():
    """
    Unit test for the root endpoint.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI Backend!"}

# Example of testing a function that might interact with an external service
# This is more of an integration test, but demonstrates mocking external calls
def some_internal_function_that_uses_external_api():
    # This function would be part of your actual application logic
    # For demonstration, let's assume it calls an external API
    import requests
    try:
        response = requests.get("http://external.api/data")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def test_some_internal_function_with_mocked_external_api():
    """
    Demonstrates mocking an external API call within a unit test.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "mocked_data"}
    mock_response.raise_for_status.return_value = None # No exception

    with patch('requests.get', return_value=mock_response) as mock_get:
        result = some_internal_function_that_uses_external_api()
        assert result == {"data": "mocked_data"}
        mock_get.assert_called_once_with("http://external.api/data")

    # Test error case
    mock_response_error = MagicMock()
    mock_response_error.raise_for_status.side_effect = requests.exceptions.RequestException("Network error")
    with patch('requests.get', return_value=mock_response_error):
        result = some_internal_function_that_uses_external_api()
        assert "error" in result
        assert "Network error" in result["error"]