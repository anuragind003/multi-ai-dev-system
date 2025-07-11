import pytest
from fastapi.testclient import TestClient
from locust import HttpUser, task, between

from app.main import app
from app.core.config import settings

# --- Unit Tests ---
def test_health_check_unit():
    """
    Unit test for the health check endpoint.
    Ensures the endpoint returns the correct status and environment.
    """
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "environment": settings.ENVIRONMENT}

def test_root_endpoint_unit():
    """
    Unit test for the root endpoint.
    """
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to the FastAPI Monorepo Backend!"}

# --- Integration Tests ---
@pytest.fixture(scope="module")
def client():
    """
    Fixture to provide a TestClient for integration tests.
    """
    with TestClient(app) as c:
        yield c

def test_create_item_integration(client):
    """
    Integration test for creating an item.
    """
    item_data = {"name": "Test Item", "description": "A test item", "price": 10.99}
    response = client.post("/items/", json=item_data)
    assert response.status_code == 201
    assert response.json()["name"] == "Test Item"
    assert "price" in response.json()

def test_read_item_integration(client):
    """
    Integration test for reading an item.
    """
    # Assuming item_id 1 exists based on main.py example
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Example Item"

def test_read_non_existent_item_integration(client):
    """
    Integration test for reading a non-existent item.
    """
    response = client.get("/items/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"

def test_invalid_item_creation_integration(client):
    """
    Integration test for creating an item with invalid data (e.g., missing required fields).
    """
    invalid_item_data = {"description": "Missing name and price"}
    response = client.post("/items/", json=invalid_item_data)
    assert response.status_code == 422 # Unprocessable Entity due to validation error
    assert "detail" in response.json()
    assert any("name" in error["loc"] for error in response.json()["detail"])
    assert any("price" in error["loc"] for error in response.json()["detail"])

# --- Performance Tests (Locust) ---
# To run these tests, save this file as e.g., `locustfile.py` and run `locust -f locustfile.py`
# Then open http://localhost:8089 in your browser.
class WebsiteUser(HttpUser):
    """
    Locust user class for performance testing the FastAPI application.
    """
    wait_time = between(1, 2.5)  # Users wait between 1 and 2.5 seconds between tasks

    @task(3) # Higher weight means this task is run more often
    def get_health(self):
        """
        Simulates users checking the health endpoint.
        """
        self.client.get("/health", name="/health [GET]")

    @task(1)
    def create_and_read_item(self):
        """
        Simulates users creating an item and then reading a specific item.
        """
        # Create item
        item_data = {"name": "Perf Test Item", "description": "Created by performance test", "price": 99.99}
        create_response = self.client.post("/items/", json=item_data, name="/items/ [POST]")
        if create_response.status_code == 201:
            # Read item (using a fixed ID for simplicity in perf test)
            self.client.get("/items/1", name="/items/{item_id} [GET]")
        else:
            create_response.failure("Failed to create item")

    @task(2)
    def get_root(self):
        """
        Simulates users accessing the root endpoint.
        """
        self.client.get("/", name="/ [GET]")

# Note: For CI/CD, Locust can be run in headless mode to generate reports:
# locust -f backend/app/tests/test_api.py --host http://localhost:8000 --headless -u 100 -r 10 -t 30s --csv=test_results --html=test_report.html