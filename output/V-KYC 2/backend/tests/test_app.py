import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Service is healthy", "service": "FastAPI Backend"}

def test_create_item():
    item_data = {
        "name": "Test Item",
        "description": "A test item for unit testing",
        "price": 10.99,
        "tax": 1.50
    }
    response = client.post("/api/items/", json=item_data)
    assert response.status_code == 201
    assert response.json()["message"] == "Item created successfully"
    assert response.json()["item"]["name"] == "Test Item"

def test_read_existing_item():
    response = client.get("/api/items/1")
    assert response.status_code == 200
    assert response.json()["item_id"] == 1
    assert "name" in response.json()

def test_read_non_existing_item():
    response = client.get("/api/items/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"