import pytest
import httpx
from fastapi.testclient import TestClient
from backend.app.main import app

# Using TestClient for direct FastAPI app testing
client = TestClient(app)

# Using httpx for more realistic HTTP requests (e.g., against a running Docker container)
# For this example, we'll stick to TestClient for simplicity, but httpx is good for
# hitting a live server.
# BASE_URL = "http://localhost:8000" # If testing against a running docker container

@pytest.mark.asyncio
async def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI Monolithic App!"}

@pytest.mark.asyncio
async def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_read_item_success():
    response = client.get("/items/42")
    assert response.status_code == 200
    assert response.json() == {"item_id": 42, "name": "The Answer"}

@pytest.mark.asyncio
async def test_read_item_not_found():
    response = client.get("/items/999")
    assert response.status_code == 404
    assert response.json() == {"message": "Item not found"}

@pytest.mark.asyncio
async def test_non_existent_endpoint():
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"message": "Not Found - The requested URL does not exist."}

# Example of a test that might require a database connection
# @pytest.mark.asyncio
# async def test_create_user_with_db(db_session): # Assuming db_session fixture
#     # Test logic that interacts with the database
#     pass