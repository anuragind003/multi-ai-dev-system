import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_read_root():
    """
    Test the root endpoint for a successful response.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, FastAPI! This is a monitoring demo."}

@pytest.mark.asyncio
async def test_read_even_item():
    """
    Test the /items/{item_id} endpoint with an even item_id.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/items/2")
    assert response.status_code == 200
    assert response.json() == {"item_id": 2, "message": "Even item"}

@pytest.mark.asyncio
async def test_read_odd_item_not_found():
    """
    Test the /items/{item_id} endpoint with an odd item_id (simulated 404).
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/items/3")
    assert response.status_code == 404
    assert response.json() == {"message": "Odd item not found (simulated error)"}

@pytest.mark.asyncio
async def test_health_check():
    """
    Test the health check endpoint.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_simulate_error():
    """
    Test the simulate_error endpoint for a 500 response.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/simulate_error")
    assert response.status_code == 500
    assert response.json() == {"message": "Simulated internal server error"}

@pytest.mark.asyncio
async def test_metrics_endpoint_exists():
    """
    Test that the /metrics endpoint is accessible and returns text.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text