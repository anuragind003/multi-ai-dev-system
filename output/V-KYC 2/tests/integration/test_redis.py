import pytest
import httpx
import os
import time

# Assuming the app is running on localhost:8000 and Redis on localhost:6379
# These tests require the docker-compose.yml services to be running
# (i.e., `docker compose up -d` before running these tests)

BASE_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_redis_connection_via_health_check():
    """
    Tests if the FastAPI app can connect to Redis via its health check endpoint.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["redis"] == "connected"

@pytest.mark.asyncio
async def test_set_and_get_cache_integration():
    """
    Tests setting and getting a value from Redis through the FastAPI app.
    """
    key = "integration_test_key"
    value = "integration_test_value"
    ttl = 10 # seconds

    async with httpx.AsyncClient() as client:
        # Set cache
        response = await client.post(f"{BASE_URL}/cache", json={"key": key, "value": value, "ttl": ttl})
        assert response.status_code == 200
        assert f"Key '{key}' set in cache with TTL {ttl}s" in response.json()["message"]

        # Get cache
        response = await client.get(f"{BASE_URL}/cache/{key}")
        assert response.status_code == 200
        assert response.json()["key"] == key
        assert response.json()["value"] == value

        # Wait for TTL to expire and check
        print(f"Waiting for {ttl} seconds for key '{key}' to expire...")
        time.sleep(ttl + 1) # Wait a bit more than TTL
        response = await client.get(f"{BASE_URL}/cache/{key}")
        assert response.status_code == 404
        assert f"Key '{key}' not found in cache." in response.json()["detail"]

@pytest.mark.asyncio
async def test_session_counter_integration():
    """
    Tests the session counter functionality, ensuring Redis increments correctly.
    """
    async with httpx.AsyncClient() as client:
        # First request - should get a new session ID and count 1
        response1 = await client.get(f"{BASE_URL}/session_counter")
        assert response1.status_code == 200
        data1 = response1.json()
        assert "session_id" in data1
        assert data1["visits"] == 1
        session_id = data1["session_id"]
        assert "session_id" in response1.cookies

        # Second request with the same session ID - should increment count to 2
        response2 = await client.get(f"{BASE_URL}/session_counter", cookies={"session_id": session_id})
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["session_id"] == session_id
        assert data2["visits"] == 2

        # Third request with the same session ID - should increment count to 3
        response3 = await client.get(f"{BASE_URL}/session_counter", cookies={"session_id": session_id})
        assert response3.status_code == 200
        data3 = response3.json()
        assert data3["session_id"] == session_id
        assert data3["visits"] == 3