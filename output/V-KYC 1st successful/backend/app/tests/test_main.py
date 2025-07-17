from fastapi.testclient import TestClient
from app.main import app

# Initialize TestClient for FastAPI application
client = TestClient(app)

def test_read_root():
    """
    Test the root endpoint to ensure it returns the correct message and status code.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from FastAPI Backend! This is a secure and scalable service."}

def test_health_check():
    """
    Test the health check endpoint to ensure it returns 'ok' status.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "timestamp" in response.json()

def test_read_item_success():
    """
    Test reading an item with a valid ID.
    """
    item_id = 123
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 200
    assert response.json() == {"item_id": item_id, "name": f"Item {item_id}", "description": "This is a sample item."}

def test_read_item_not_found():
    """
    Test reading an item with an ID that should result in a 404.
    """
    item_id = 404
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 404
    assert response.json() == {"message": "Oops! Item not found"}

def test_metrics_endpoint():
    """
    Test that the Prometheus metrics endpoint is accessible.
    """
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text

def test_config_endpoint():
    """
    Test the config endpoint to ensure it returns expected configuration.
    """
    response = client.get("/config")
    assert response.status_code == 200
    # In a test environment, SECRET_KEY might not be set, so we check for its status
    assert "secret_key_status" in response.json()
    assert "environment" in response.json()
    assert response.json()["environment"] == "development" # Default in main.py if APP_ENV not set