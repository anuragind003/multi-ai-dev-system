import pytest
from fastapi.testclient import TestClient
from app.main import app, settings

# Override settings for testing
@pytest.fixture(scope="session", autouse=True)
def override_settings():
    settings.ENVIRONMENT = "test"
    settings.LOG_LEVEL = "DEBUG"
    # Override database URL for tests if needed
    # settings.DATABASE_URL = "sqlite:///./test_db.db"

@pytest.fixture(scope="module")
def client():
    """
    Fixture for FastAPI TestClient.
    """
    with TestClient(app) as c:
        yield c

# Example of a mock database fixture (if you had a DB dependency)
# @pytest.fixture(scope="function")
# def mock_db():
#     # Setup mock database or clear test database
#     print("Setting up mock DB...")
#     yield "mock_db_connection"
#     # Teardown mock database
#     print("Tearing down mock DB...")