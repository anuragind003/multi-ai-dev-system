# tests/test_suite.py
# This file combines unit, integration, and a placeholder for performance test setup.

import pytest
from fastapi.testclient import TestClient
from app.main import app, db, next_item_id, Item, ItemCreate
import os
import time

# --- Unit Tests ---
# These tests focus on individual functions or components in isolation.
# For a real application, you'd mock external dependencies like databases.

def test_health_check_unit():
    # This is a basic unit test for the health check endpoint.
    # In a true unit test, you might mock the check_db_connection function.
    # For simplicity, we're calling the actual endpoint via TestClient.
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_read_items_empty_unit():
    # Test reading items when the database is empty (after clearing)
    original_db = list(db) # Save original state
    db.clear() # Clear the in-memory db for this test
    client = TestClient(app)
    response = client.get("/items/")
    assert response.status_code == 200
    assert response.json() == []
    db.extend(original_db) # Restore original state

# --- Integration Tests ---
# These tests verify the interaction between different components,
# such as the API endpoints and the in-memory database.

@pytest.fixture(scope="module")
def client():
    """Provides a TestClient instance for integration tests."""
    # Reset the in-memory database for a clean slate for integration tests
    global db, next_item_id
    db.clear()
    next_item_id = 1
    # Add initial data for tests
    db.append(Item(id=next_item_id, name="Test Item 1", description="Desc 1", price=10.0))
    next_item_id += 1
    db.append(Item(id=next_item_id, name="Test Item 2", description="Desc 2", price=20.0))
    next_item_id += 1
    with TestClient(app) as c:
        yield c
    # Clean up after tests if necessary (though in-memory db is reset by fixture)
    db.clear()
    next_item_id = 1

def test_read_items_integration(client):
    response = client.get("/items/")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Test Item 1"

def test_create_item_integration(client):
    item_data = {"name": "New Test Item", "description": "A newly created item", "price": 30.0}
    response = client.post("/items/", json=item_data)
    assert response.status_code == 201
    created_item = response.json()
    assert created_item["name"] == "New Test Item"
    assert created_item["id"] is not None
    assert len(db) == 3 # Check if added to in-memory db

def test_read_single_item_integration(client):
    # Assuming item with ID 1 exists from fixture setup
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Item 1"

def test_read_nonexistent_item_integration(client):
    response = client.get("/items/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"

# --- Performance Test Placeholder ---
# For actual performance testing, you would typically use a dedicated tool like Locust
# and run it against a deployed instance of your application, not directly within pytest.
# This function serves as a placeholder to show how it might be invoked or tested in CI.

def test_performance_placeholder():
    """
    This is a placeholder for performance tests.
    In a real scenario, you would run Locust or similar tools.
    Example: locust -f tests/performance/locustfile.py --host http://localhost:8000 --headless -u 10 -r 2 --run-time 30s --csv=performance_results
    """
    print("\n--- Running Performance Test Placeholder ---")
    print("This test does not execute actual load. It serves as a reminder to run Locust.")
    print("To run Locust locally: locust -f tests/performance/locustfile.py --host http://localhost:8000")
    print("To run Locust in headless mode for CI: locust -f tests/performance/locustfile.py --host http://<YOUR_DEPLOYED_APP_IP>:8000 --headless -u 10 -r 2 --run-time 30s --csv=performance_results")
    # Simulate a very short "test" that always passes
    time.sleep(0.1)
    assert True
    print("--- Performance Test Placeholder Finished ---")

# You can create a separate file for Locust scenarios like tests/performance/locustfile.py
# Example locustfile.py content:
"""
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 2.5) # Users wait between 1 and 2.5 seconds between tasks

    @task(3) # 3 times more likely to be picked than other tasks
    def get_health(self):
        self.client.get("/health")

    @task(5)
    def get_items(self):
        self.client.get("/items/?skip=0&limit=10")

    @task(1)
    def create_item(self):
        item_data = {"name": "Load Test Item", "description": "Created by load test", "price": 99.99}
        self.client.post("/items/", json=item_data)

    @task(2)
    def get_single_item(self):
        # Assuming item IDs are sequential and start from 1
        item_id = self.environment.stats.num_requests % 10 + 1 # Cycle through first 10 items
        self.client.get(f"/items/{item_id}")
"""