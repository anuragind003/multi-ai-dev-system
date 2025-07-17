import pytest
import httpx
import os
from dotenv import load_dotenv

# Load environment variables for the test client
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Determine the base URL for the API
# In CI/CD, this might be a Docker service name, locally it's localhost
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

@pytest.mark.asyncio
async def test_read_root_integration():
    """
    Integration test for the root endpoint.
    """
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to the FastAPI Operational Backend!"}

@pytest.mark.asyncio
async def test_health_check_integration():
    """
    Integration test for the health check endpoint.
    """
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "version" in response.json()

@pytest.mark.asyncio
async def test_create_and_read_item_integration():
    """
    Integration test for creating and reading an item.
    """
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        # Test POST /items/
        new_item = {
            "name": "Test Item",
            "description": "This is a test item.",
            "price": 99.99,
            "tax": 5.0
        }
        post_response = await client.post("/items/", json=new_item)
        assert post_response.status_code == 200
        created_item = post_response.json()
        assert created_item["name"] == new_item["name"]
        assert created_item["price"] == new_item["price"]

        # Test GET /items/{item_id} (using a known ID from main.py for simplicity)
        get_response = await client.get("/items/1")
        assert get_response.status_code == 200
        retrieved_item = get_response.json()
        assert retrieved_item["name"] == "Foo"
        assert retrieved_item["price"] == 12.5

        # Test GET /items/{item_id} for non-existent item
        not_found_response = await client.get("/items/999")
        assert not_found_response.status_code == 404
        assert not_found_response.json()["detail"] == "Item not found"