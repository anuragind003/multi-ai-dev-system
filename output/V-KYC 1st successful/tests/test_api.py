import pytest
from httpx import AsyncClient
from main import app
from unittest.mock import AsyncMock, patch, MagicMock
from database import get_db
from security import get_api_key, has_role
from models import IntegrationTest, TestResult
from schemas import TestResponse, TestResultResponse
from datetime import datetime

# Mock database dependency
@pytest.fixture
async def mock_db_session():
    """Fixture for a mock SQLAlchemy AsyncSession."""
    session = AsyncMock()
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value.scalars.return_value.all.return_value = []
    yield session

# Override dependencies for testing
@pytest.fixture(autouse=True)
def override_dependencies(app, mock_db_session):
    """Overrides FastAPI dependencies for testing."""
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_api_key] = lambda: "test_api_key" # Always return a valid key
    app.dependency_overrides[has_role] = lambda required_roles: True # Always authorize
    yield
    app.dependency_overrides = {} # Clear overrides after test

@pytest.fixture
async def client():
    """Fixture for an asynchronous test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_test_success(client, mock_db_session):
    """Test POST /api/v1/tests - successful creation."""
    test_data = {"name": "New API Test", "description": "API Test Desc", "test_type": "Backend-DB"}
    
    response = await client.post("/api/v1/tests", json=test_data, headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 201
    assert response.json()["name"] == "New API Test"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_create_test_conflict(client, mock_db_session):
    """Test POST /api/v1/tests - conflict (test name exists)."""
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = IntegrationTest(id=1, name="Existing Test")
    test_data = {"name": "Existing Test", "description": "API Test Desc", "test_type": "Backend-DB"}
    
    response = await client.post("/api/v1/tests", json=test_data, headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_test_validation_error(client):
    """Test POST /api/v1/tests - validation error (missing name)."""
    test_data = {"description": "API Test Desc", "test_type": "Backend-DB"}
    
    response = await client.post("/api/v1/tests", json=test_data, headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 422
    assert "validation error" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_get_all_tests_success(client, mock_db_session):
    """Test GET /api/v1/tests - successful retrieval of all tests."""
    mock_tests = [
        IntegrationTest(id=1, name="Test A", test_type="Backend-DB"),
        IntegrationTest(id=2, name="Test B", test_type="Backend-NFS")
    ]
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = mock_tests
    
    response = await client.get("/api/v1/tests", headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Test A"

@pytest.mark.asyncio
async def test_get_test_by_id_success(client, mock_db_session):
    """Test GET /api/v1/tests/{test_id} - successful retrieval by ID."""
    mock_test = IntegrationTest(id=1, name="Single Test", test_type="Backend-DB")
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_test
    
    response = await client.get("/api/v1/tests/1", headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 200
    assert response.json()["name"] == "Single Test"

@pytest.mark.asyncio
async def test_get_test_by_id_not_found(client, mock_db_session):
    """Test GET /api/v1/tests/{test_id} - test not found."""
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
    
    response = await client.get("/api/v1/tests/999", headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_test_success(client, mock_db_session):
    """Test PUT /api/v1/tests/{test_id} - successful update."""
    existing_test = IntegrationTest(id=1, name="Old Name", test_type="Backend-DB")
    mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [
        existing_test, # For get_test
        None # For name conflict check
    ]
    
    update_data = {"name": "Updated Name", "description": "New Desc"}
    response = await client.put("/api/v1/tests/1", json=update_data, headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_update_test_not_found(client, mock_db_session):
    """Test PUT /api/v1/tests/{test_id} - test not found."""
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
    update_data = {"name": "Updated Name"}
    
    response = await client.put("/api/v1/tests/999", json=update_data, headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_test_success(client, mock_db_session):
    """Test DELETE /api/v1/tests/{test_id} - successful deletion."""
    mock_test = IntegrationTest(id=1, name="Test to Delete", test_type="Backend-DB")
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_test
    
    response = await client.delete("/api/v1/tests/1", headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]
    mock_db_session.delete.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_delete_test_not_found(client, mock_db_session):
    """Test DELETE /api/v1/tests/{test_id} - test not found."""
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
    
    response = await client.delete("/api/v1/tests/999", headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@pytest.mark.asyncio
@patch('services.IntegrationTestService.execute_test', new_callable=AsyncMock)
async def test_execute_test_success(mock_execute_test, client, mock_db_session):
    """Test POST /api/v1/tests/{test_id}/execute - successful execution."""
    mock_test = IntegrationTest(id=1, name="Test to Execute", test_type="Backend-DB", status="Active")
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_test # For get_test in service
    
    mock_result = TestResult(id=101, test_id=1, status="Passed", output="Test OK", run_time_ms=50)
    mock_execute_test.return_value = mock_result
    
    response = await client.post("/api/v1/tests/1/execute", headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 200
    assert response.json()["status"] == "Passed"
    assert response.json()["output"] == "Test OK"
    mock_execute_test.assert_called_once_with(1, "API_User")

@pytest.mark.asyncio
async def test_api_key_missing(client):
    """Test API key authentication - missing key."""
    response = await client.get("/api/v1/tests")
    assert response.status_code == 401
    assert "API Key is missing" in response.json()["detail"]

@pytest.mark.asyncio
async def test_api_key_invalid(client):
    """Test API key authentication - invalid key."""
    response = await client.get("/api/v1/tests", headers={"X-API-Key": "wrong_key"})
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]

@pytest.mark.asyncio
@patch('security.has_role', side_effect=MagicMock(return_value=False)) # Mock has_role to always return False
async def test_authorization_failure(mock_has_role, client):
    """Test authorization failure."""
    # This test assumes that `has_role` raises ForbiddenException when it returns False
    # The actual implementation of `has_role` in security.py raises ForbiddenException
    # So, we just need to ensure it's called and the correct status is returned.
    
    # We need to mock the dependency override for has_role to simulate a failure
    # Temporarily remove the global override for has_role
    app.dependency_overrides.pop(has_role, None)
    
    # Now, set up a specific mock for this test that raises ForbiddenException
    async def mock_forbidden_role_check(required_roles):
        raise ForbiddenException(detail="Access denied for test.")
    app.dependency_overrides[has_role] = mock_forbidden_role_check

    response = await client.post("/api/v1/tests", json={"name": "Auth Test", "description": "Desc", "test_type": "Backend-DB"}, headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]
    
    # Clean up the specific override
    app.dependency_overrides.pop(has_role, None)

@pytest.mark.asyncio
async def test_health_check_basic(client):
    """Test GET /api/v1/health - basic health check."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "OK"
    assert "timestamp" in response.json()

@pytest.mark.asyncio
@patch('routers.health.os.path.exists', return_value=True)
@patch('routers.health.httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_health_check_deep_success(mock_get, mock_os_path_exists, client):
    """Test GET /api/v1/health/deep - successful deep health check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_get.return_value.__aenter__.return_value = mock_response
    
    response = await client.get("/api/v1/health/deep", headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 200
    assert response.json()["status"] == "OK"
    assert len(response.json()["components"]) == 3
    assert all(c["status"] == "OK" for c in response.json()["components"])

@pytest.mark.asyncio
@patch('routers.health.os.path.exists', return_value=False) # Simulate NFS failure
@patch('routers.health.httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_health_check_deep_degraded(mock_get, mock_os_path_exists, client):
    """Test GET /api/v1/health/deep - degraded health check (NFS failure)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_get.return_value.__aenter__.return_value = mock_response
    
    response = await client.get("/api/v1/health/deep", headers={"X-API-Key": "test_api_key"})
    
    assert response.status_code == 503
    assert response.json()["status"] == "Degraded"
    nfs_component = next((c for c in response.json()["components"] if c["name"] == "NFS"), None)
    assert nfs_component is not None
    assert nfs_component["status"] == "Critical"
    assert "does not exist" in nfs_component["details"]