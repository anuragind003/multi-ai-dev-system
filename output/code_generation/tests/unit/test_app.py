import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to the FastAPI Production Service!" in response.json()["message"]

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Service is healthy"}

def test_create_item():
    item_data = {"name": "Test Item", "description": "A test item", "price": 10.99}
    response = client.post("/items/", json=item_data)
    assert response.status_code == 201
    assert response.json()["name"] == "Test Item"
    assert response.json()["price"] == 10.99

def test_read_item_existing():
    response = client.get("/items/2") # Even ID should exist
    assert response.status_code == 200
    assert response.json()["name"] == "Item 2"

def test_read_item_not_found():
    response = client.get("/items/1") # Odd ID should not exist
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"

def test_get_config():
    response = client.get("/config")
    assert response.status_code == 200
    # In unit tests, environment variables are not set from .env.example
    # They would be default or mocked.
    assert response.json()["my_secret_key"] == "default_secret_value"