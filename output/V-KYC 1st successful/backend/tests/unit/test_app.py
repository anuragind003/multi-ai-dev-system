import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, HealthCheckResponse, Item

# Initialize TestClient for FastAPI application
client = TestClient(app)

def test_read_root():
    """
    Test the root endpoint to ensure it returns the expected welcome message.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "Welcome to the FastAPI Backend!"
    assert "app_name" in response.json()

def test_health_check():
    """
    Test the health check endpoint.
    """
    response = client.get("/health")
    assert response.status_code == 200
    health_response = HealthCheckResponse(**response.json())
    assert health_response.status == "ok"
    assert health_response.message == "Service is healthy"
    assert health_response.version == "1.0.0" # Assuming default version
    assert health_response.environment in ["development", "production"] # Can be either based on env

def test_create_item():
    """
    Test the item creation endpoint.
    """
    item_data = {"name": "Test Item", "description": "A test item", "price": 10.0, "tax": 1.0}
    response = client.post("/items/", json=item_data)
    assert response.status_code == 201
    created_item = Item(**response.json())
    assert created_item.name == item_data["name"]
    assert created_item.price == item_data["price"]

def test_read_item_existing():
    """
    Test retrieving an existing item.
    """
    response = client.get("/items/1")
    assert response.status_code == 200
    item = Item(**response.json())
    assert item.name == "Sample Item"
    assert item.price == 10.99

def test_read_item_not_found():
    """
    Test retrieving a non-existent item.
    """
    response = client.get("/items/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"

# You can add more unit tests for specific functions or logic within your app.
# For example, if you had a utility function:
# from backend.app.utils import calculate_tax
# def test_calculate_tax():
#     assert calculate_tax(100, 0.1) == 10.0