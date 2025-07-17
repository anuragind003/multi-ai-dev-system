import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone

from main import app
from app.core.database import get_db, Base, engine
from app.models.bulk_download import DownloadRequest, FileMetadata
from app.schemas.bulk_download import DownloadStatus, BulkDownloadRequest, BulkDownloadResponse
from app.utils.file_operations import MOCK_NFS_FILES, generate_mock_file_path
from app.core.security import create_access_token, USERS_DB

# Override the database dependency for testing
@pytest.fixture(name="db_session")
async def db_session_fixture():
    """
    Fixture for a clean database session for each test.
    Uses an in-memory SQLite database for speed.
    """
    # Use a separate in-memory SQLite database for testing
    test_engine = engine
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(test_engine) as session:
        yield session
        await session.close()

# Override the get_db dependency in the FastAPI app
app.dependency_overrides[get_db] = db_session_fixture

@pytest.fixture(name="client")
async def client_fixture(db_session: AsyncSession):
    """
    Fixture for an asynchronous test client.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture(name="auth_token")
def auth_token_fixture():
    """
    Fixture to get an authentication token for a test user.
    """
    user = USERS_DB["testuser"]
    token = create_access_token(data={"sub": user["username"], "roles": user["roles"]})
    return token

@pytest.mark.asyncio
async def test_initiate_bulk_download_success(client: AsyncClient, auth_token: str):
    """
    Test successful initiation of a bulk download request.
    All files are expected to exist.
    """
    lan_ids = ["LAN1234567890", "LAN0987654321"]
    request_payload = {"lan_ids": lan_ids}

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await client.post("/api/v1/downloads/bulk-download", json=request_payload, headers=headers)

    assert response.status_code == 202
    response_data = response.json()
    assert response_data["success"] is True
    assert "request_id" in response_data["data"]
    assert response_data["data"]["status"] == DownloadStatus.COMPLETED.value
    assert response_data["data"]["total_lan_ids"] == len(lan_ids)
    assert len(response_data["data"]["processed_files"]) == len(lan_ids)

    for file_data in response_data["data"]["processed_files"]:
        assert file_data["file_exists"] is True
        assert file_data["file_size_bytes"] is not None
        assert file_data["last_modified_at"] is not None
        assert file_data["error_message"] is None

@pytest.mark.asyncio
async def test_initiate_bulk_download_partial_success(client: AsyncClient, auth_token: str):
    """
    Test bulk download request with some files existing and some not.
    """
    lan_ids = ["LAN1234567890", "LAN1122334455"] # One exists, one doesn't
    request_payload = {"lan_ids": lan_ids}

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await client.post("/api/v1/downloads/bulk-download", json=request_payload, headers=headers)

    assert response.status_code == 202
    response_data = response.json()
    assert response_data["success"] is True
    assert response_data["data"]["status"] == DownloadStatus.PARTIAL_SUCCESS.value
    assert response_data["data"]["total_lan_ids"] == len(lan_ids)
    assert len(response_data["data"]["processed_files"]) == len(lan_ids)

    found_file = next(f for f in response_data["data"]["processed_files"] if f["lan_id"] == "LAN1234567890")
    not_found_file = next(f for f in response_data["data"]["processed_files"] if f["lan_id"] == "LAN1122334455")

    assert found_file["file_exists"] is True
    assert found_file["error_message"] is None
    assert not_found_file["file_exists"] is False
    assert "File not found on NFS." in not_found_file["error_message"]

@pytest.mark.asyncio
async def test_initiate_bulk_download_all_failed(client: AsyncClient, auth_token: str):
    """
    Test bulk download request where all files fail to be found.
    """
    lan_ids = ["LAN_NON_EXISTENT_1", "LAN_NON_EXISTENT_2"]
    request_payload = {"lan_ids": lan_ids}

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await client.post("/api/v1/downloads/bulk-download", json=request_payload, headers=headers)

    assert response.status_code == 202
    response_data = response.json()
    assert response_data["success"] is True
    assert response_data["data"]["status"] == DownloadStatus.FAILED.value
    assert response_data["data"]["total_lan_ids"] == len(lan_ids)
    assert len(response_data["data"]["processed_files"]) == len(lan_ids)

    for file_data in response_data["data"]["processed_files"]:
        assert file_data["file_exists"] is False
        assert "File not found on NFS." in file_data["error_message"]

@pytest.mark.asyncio
async def test_get_bulk_download_status_success(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    Test retrieving the status of an existing bulk download request.
    """
    # First, create a request directly in the DB for testing retrieval
    request_id = str(uuid.uuid4())
    test_request = DownloadRequest(
        id=request_id,
        status=DownloadStatus.COMPLETED.value,
        requested_by="testuser",
        total_lan_ids=1,
        requested_at=datetime.now(timezone.utc),
        processed_at=datetime.now(timezone.utc)
    )
    test_file_meta = FileMetadata(
        request_id=request_id,
        lan_id="LAN1234567890",
        file_path=generate_mock_file_path("LAN1234567890"),
        file_exists=True,
        file_size_bytes=1000,
        last_modified_at=datetime.now(timezone.utc)
    )
    db_session.add(test_request)
    db_session.add(test_file_meta)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await client.get(f"/api/v1/downloads/bulk-download/{request_id}", headers=headers)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    assert response_data["data"]["request_id"] == request_id
    assert response_data["data"]["status"] == DownloadStatus.COMPLETED.value
    assert len(response_data["data"]["processed_files"]) == 1
    assert response_data["data"]["processed_files"][0]["lan_id"] == "LAN1234567890"

@pytest.mark.asyncio
async def test_get_bulk_download_status_not_found(client: AsyncClient, auth_token: str):
    """
    Test retrieving status for a non-existent request ID.
    """
    non_existent_id = "non-existent-uuid"
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await client.get(f"/api/v1/downloads/bulk-download/{non_existent_id}", headers=headers)

    assert response.status_code == 404
    response_data = response.json()
    assert response_data["success"] is False
    assert "Bulk Download Request not found." in response_data["message"]

@pytest.mark.asyncio
async def test_initiate_bulk_download_validation_error(client: AsyncClient, auth_token: str):
    """
    Test input validation for bulk download request (e.g., empty list, too many items).
    """
    # Test empty list
    request_payload_empty = {"lan_ids": []}
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await client.post("/api/v1/downloads/bulk-download", json=request_payload_empty, headers=headers)
    assert response.status_code == 422
    assert "Validation Error" in response.json()["message"]

    # Test too many items (max 10)
    request_payload_too_many = {"lan_ids": [f"LAN{i}" for i in range(12)]}
    response = await client.post("/api/v1/downloads/bulk-download", json=request_payload_too_many, headers=headers)
    assert response.status_code == 422
    assert "Validation Error" in response.json()["message"]

    # Test non-alphanumeric LAN ID
    request_payload_invalid_char = {"lan_ids": ["LAN123!", "LAN456"]}
    response = await client.post("/api/v1/downloads/bulk-download", json=request_payload_invalid_char, headers=headers)
    assert response.status_code == 422
    assert "Validation Error" in response.json()["message"]
    assert "All LAN IDs must be alphanumeric strings." in str(response.json()["data"])

    # Test duplicate LAN IDs
    request_payload_duplicate = {"lan_ids": ["LAN123", "LAN123"]}
    response = await client.post("/api/v1/downloads/bulk-download", json=request_payload_duplicate, headers=headers)
    assert response.status_code == 422
    assert "Validation Error" in response.json()["message"]
    assert "Duplicate LAN IDs are not allowed in a single request." in str(response.json()["data"])


@pytest.mark.asyncio
async def test_authentication_required(client: AsyncClient):
    """
    Test that endpoints require authentication.
    """
    lan_ids = ["LAN1234567890"]
    request_payload = {"lan_ids": lan_ids}

    response = await client.post("/api/v1/downloads/bulk-download", json=request_payload)
    assert response.status_code == 401
    assert "Authentication required or failed." in response.json()["message"]

    response = await client.get("/api/v1/downloads/bulk-download/some-id")
    assert response.status_code == 401
    assert "Authentication required or failed." in response.json()["message"]

@pytest.mark.asyncio
async def test_rate_limit_middleware(client: AsyncClient, auth_token: str):
    """
    Test the rate limiting middleware.
    Note: This test might be flaky if run in parallel or if the rate limit is too high.
    Adjust settings.RATE_LIMIT_CALLS_PER_MINUTE for testing.
    """
    # Temporarily set a low rate limit for testing
    original_rate_limit = app.state.rate_limit_calls_per_minute
    app.state.rate_limit_calls_per_minute = 2 # Allow only 2 calls per minute for this test

    lan_ids = ["LAN1234567890"]
    request_payload = {"lan_ids": lan_ids}
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Make calls within the limit
    response1 = await client.post("/api/v1/downloads/bulk-download", json=request_payload, headers=headers)
    assert response1.status_code == 202

    response2 = await client.post("/api/v1/downloads/bulk-download", json=request_payload, headers=headers)
    assert response2.status_code == 202

    # This call should exceed the limit
    response3 = await client.post("/api/v1/downloads/bulk-download", json=request_payload, headers=headers)
    assert response3.status_code == 429
    assert "Too Many Requests" in response3.json()["message"]

    # Restore original rate limit
    app.state.rate_limit_calls_per_minute = original_rate_limit