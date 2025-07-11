import pytest
from fastapi.testclient import TestClient
from backend.main import app

# Create a TestClient instance for the FastAPI application
client = TestClient(app)

def test_read_root():
    """
    Test the root endpoint to ensure it returns a 200 OK status
    and contains expected HTML content.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to the FastAPI Backend!" in response.text
    assert "text/html" in response.headers["content-type"]

def test_health_check():
    """
    Test the health check endpoint to ensure it returns a 200 OK status
    and the expected status message.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "API is healthy"}

def test_read_item():
    """
    Test retrieving an item by ID with and without a query parameter.
    """
    # Test without query parameter
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json() == {"item_id": 1, "q": None, "message": "Item retrieved successfully"}

    # Test with query parameter
    response = client.get("/items/2?q=testquery")
    assert response.status_code == 200
    assert response.json() == {"item_id": 2, "q": "testquery", "message": "Item retrieved successfully"}

def test_create_item():
    """
    Test creating a new item, ensuring a 201 Created status and correct data.
    """
    item_data = {
        "name": "Test Item",
        "description": "This is a test item.",
        "price": 10.99,
        "tax": 1.50
    }
    response = client.post("/items/", json=item_data)
    assert response.status_code == 201
    response_json = response.json()
    assert response_json["message"] == "Item created successfully"
    assert response_json["item"]["name"] == item_data["name"]
    assert response_json["item"]["price"] == item_data["price"]

def test_create_item_invalid_data():
    """
    Test creating an item with invalid data (e.g., missing required fields)
    to ensure proper validation error handling.
    """
    invalid_item_data = {
        "description": "Missing name and price"
    }
    response = client.post("/items/", json=invalid_item_data)
    assert response.status_code == 422  # Unprocessable Entity for validation errors
    assert "detail" in response.json()
    assert any("name" in error["loc"] for error in response.json()["detail"])
    assert any("price" in error["loc"] for error in response.json()["detail"])

def test_metrics_endpoint():
    """
    Test the Prometheus metrics endpoint to ensure it returns plain text
    and contains expected metric names.
    """
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds_bucket" in response.text