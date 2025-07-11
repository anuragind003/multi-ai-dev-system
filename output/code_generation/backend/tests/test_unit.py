import pytest
from backend.app.main import read_root, health_check

@pytest.mark.asyncio
async def test_read_root_unit():
    """
    Unit test for the root endpoint's message.
    """
    response = await read_root()
    assert response == {"message": "Welcome to the FastAPI Operational Backend!"}

@pytest.mark.asyncio
async def test_health_check_unit():
    """
    Unit test for the health check endpoint's status.
    Note: This is a simplified unit test. A true unit test would mock dependencies.
    For FastAPI, integration tests are often more practical for endpoints.
    """
    response = await health_check()
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"} # Assuming default version