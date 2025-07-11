import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI Monorepo Backend!"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Backend is healthy"}

def test_read_item_unauthorized():
    response = client.get("/items/1")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_read_item_authorized():
    # This test requires a valid token. For unit tests, we can mock or use a known token.
    # In a real scenario, you'd generate a test token.
    headers = {"Authorization": "Bearer supersecrettoken"}
    response = client.get("/items/1?q=test", headers=headers)
    assert response.status_code == 200
    assert response.json()["item_id"] == 1
    assert response.json()["q"] == "test"
    assert response.json()["user"]["username"] == "testuser"

def test_create_data():
    data = {"key": "value", "number": 123}
    response = client.post("/data", json=data)
    assert response.status_code == 201
    assert response.json()["message"] == "Data received"
    assert response.json()["data"] == data

def test_security_headers_present():
    response = client.get("/")
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "X-XSS-Protection" in response.headers
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "Strict-Transport-Security" in response.headers
    assert "Referrer-Policy" in response.headers
    assert "Content-Security-Policy" in response.headers