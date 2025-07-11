import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
import shutil
import zipfile
from unittest.mock import patch, MagicMock

# Adjust path for imports if running tests from root
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from config import settings
from database import Base, get_db
from models import Recording, RecordingStatus
from schemas import BulkDownloadRequest
from exceptions import NotFoundException, FileOperationError

# --- Test Database Setup ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestAsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession)

async def override_get_db():
    """Override the get_db dependency to use the test database."""
    async with TestAsyncSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

# --- Test Fixtures ---
@pytest.fixture(name="client")
async def client_fixture():
    """Async test client for FastAPI app."""
    # Create tables before tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    # Drop tables after tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    # Clean up test database file
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture(name="db_session")
async def db_session_fixture():
    """Provides a test database session."""
    async with TestAsyncSessionLocal() as session:
        yield session
        await session.rollback() # Ensure clean state after each test

@pytest.fixture(autouse=True)
def setup_teardown_temp_dir():
    """Ensures a clean temporary directory for ZIP files for each test."""
    if os.path.exists(settings.TEMP_ZIP_DIR):
        shutil.rmtree(settings.TEMP_ZIP_DIR)
    os.makedirs(settings.TEMP_ZIP_DIR, exist_ok=True)
    yield
    if os.path.exists(settings.TEMP_ZIP_DIR):
        shutil.rmtree(settings.TEMP_ZIP_DIR)

@pytest.fixture(autouse=True)
def mock_nfs_path():
    """Mocks the NFS_ROOT_PATH for testing file operations."""
    mock_nfs_root = "./mock_nfs_root"
    os.makedirs(mock_nfs_root, exist_ok=True)
    
    # Create dummy files
    os.makedirs(os.path.join(mock_nfs_root, "2023/01"), exist_ok=True)
    with open(os.path.join(mock_nfs_root, "2023/01/LAN12345_recording.mp4"), "w") as f:
        f.write("dummy content for LAN12345")
    with open(os.path.join(mock_nfs_root, "2023/01/LAN67890_recording.mp4"), "w") as f:
        f.write("dummy content for LAN67890")
    with open(os.path.join(mock_nfs_root, "2023/02/LANABCDE_recording.mp4"), "w") as f:
        f.write("dummy content for LANABCDE")

    with patch('config.settings.NFS_ROOT_PATH', mock_nfs_root):
        yield mock_nfs_root
    
    shutil.rmtree(mock_nfs_root)

# --- Test Cases ---

@pytest.mark.asyncio
async def test_bulk_download_success(client: AsyncClient, db_session: AsyncSession, mock_nfs_path: str):
    """Test successful bulk download of recordings."""
    # Arrange: Add recordings to the test DB
    rec1 = Recording(lan_id="LAN12345", file_path="2023/01/LAN12345_recording.mp4", status=RecordingStatus.AVAILABLE)
    rec2 = Recording(lan_id="LAN67890", file_path="2023/01/LAN67890_recording.mp4", status=RecordingStatus.AVAILABLE)
    db_session.add_all([rec1, rec2])
    await db_session.commit()

    request_data = BulkDownloadRequest(lan_ids=["LAN12345", "LAN67890"])

    # Act
    response = await client.post(
        "/api/v1/recordings/bulk-download",
        json=request_data.model_dump(),
        headers={"X-API-Key": settings.API_KEY}
    )

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert "X-Successful-LAN-IDs" in response.headers
    assert "X-Failed-LAN-IDs" in response.headers
    assert "LAN12345" in response.headers["X-Successful-LAN-IDs"]
    assert "LAN67890" in response.headers["X-Successful-LAN-IDs"]
    assert response.headers["X-Failed-LAN-IDs"] == "" # No failures

    # Verify the content of the zip file
    temp_zip_file = os.path.join(settings.TEMP_ZIP_DIR, "test_download.zip")
    with open(temp_zip_file, "wb") as f:
        f.write(response.content)
    
    with zipfile.ZipFile(temp_zip_file, 'r') as zipf:
        assert "LAN12345_recording.mp4" in zipf.namelist()
        assert "LAN67890_recording.mp4" in zipf.namelist()
        assert zipf.read("LAN12345_recording.mp4").decode() == "dummy content for LAN12345"
        assert zipf.read("LAN67890_recording.mp4").decode() == "dummy content for LAN67890"

@pytest.mark.asyncio
async def test_bulk_download_not_found_db(client: AsyncClient):
    """Test bulk download when recordings are not found in DB."""
    request_data = BulkDownloadRequest(lan_ids=["LAN99999"])
    response = await client.post(
        "/api/v1/recordings/bulk-download",
        json=request_data.model_dump(),
        headers={"X-API-Key": settings.API_KEY}
    )
    assert response.status_code == 404
    assert "No recordings found for the provided LAN IDs" in response.json()["detail"]

@pytest.mark.asyncio
async def test_bulk_download_file_not_found_on_nfs(client: AsyncClient, db_session: AsyncSession):
    """Test bulk download when a file is not found on NFS."""
    rec1 = Recording(lan_id="LAN12345", file_path="2023/01/LAN12345_recording.mp4", status=RecordingStatus.AVAILABLE)
    rec_missing = Recording(lan_id="LANMISSING", file_path="2023/03/LANMISSING_recording.mp4", status=RecordingStatus.AVAILABLE)
    db_session.add_all([rec1, rec_missing])
    await db_session.commit()

    request_data = BulkDownloadRequest(lan_ids=["LAN12345", "LANMISSING"])
    response = await client.post(
        "/api/v1/recordings/bulk-download",
        json=request_data.model_dump(),
        headers={"X-API-Key": settings.API_KEY}
    )
    
    assert response.status_code == 200 # Still 200 if some files are found
    assert "LAN12345" in response.headers["X-Successful-LAN-IDs"]
    assert "LANMISSING" in response.headers["X-Failed-LAN-IDs"]

    temp_zip_file = os.path.join(settings.TEMP_ZIP_DIR, "test_download_partial.zip")
    with open(temp_zip_file, "wb") as f:
        f.write(response.content)
    
    with zipfile.ZipFile(temp_zip_file, 'r') as zipf:
        assert "LAN12345_recording.mp4" in zipf.namelist()
        assert "LANMISSING_recording.mp4" not in zipf.namelist() # Missing file should not be in zip

@pytest.mark.asyncio
async def test_bulk_download_not_available_status(client: AsyncClient, db_session: AsyncSession):
    """Test bulk download when a recording is not in 'available' status."""
    rec1 = Recording(lan_id="LAN12345", file_path="2023/01/LAN12345_recording.mp4", status=RecordingStatus.AVAILABLE)
    rec_pending = Recording(lan_id="LANPENDING", file_path="2023/04/LANPENDING_recording.mp4", status=RecordingStatus.PENDING)
    db_session.add_all([rec1, rec_pending])
    await db_session.commit()

    request_data = BulkDownloadRequest(lan_ids=["LAN12345", "LANPENDING"])
    response = await client.post(
        "/api/v1/recordings/bulk-download",
        json=request_data.model_dump(),
        headers={"X-API-Key": settings.API_KEY}
    )
    
    assert response.status_code == 200
    assert "LAN12345" in response.headers["X-Successful-LAN-IDs"]
    assert "LANPENDING" in response.headers["X-Failed-LAN-IDs"]

@pytest.mark.asyncio
async def test_bulk_download_too_many_ids(client: AsyncClient):
    """Test bulk download with more than the allowed number of IDs."""
    lan_ids = [f"LAN{i:05d}" for i in range(settings.MAX_BULK_DOWNLOAD_RECORDS + 1)]
    request_data = BulkDownloadRequest(lan_ids=lan_ids)
    response = await client.post(
        "/api/v1/recordings/bulk-download",
        json=request_data.model_dump(),
        headers={"X-API-Key": settings.API_KEY}
    )
    assert response.status_code == 422 # Pydantic validation error
    assert "ensure this value has at most 10 items" in response.json()["detail"]

@pytest.mark.asyncio
async def test_bulk_download_invalid_lan_id_format(client: AsyncClient):
    """Test bulk download with an invalid LAN ID format."""
    request_data = BulkDownloadRequest(lan_ids=["INVALID_ID"])
    response = await client.post(
        "/api/v1/recordings/bulk-download",
        json=request_data.model_dump(),
        headers={"X-API-Key": settings.API_KEY}
    )
    assert response.status_code == 422
    assert "Each LAN ID must start with 'LAN' and be alphanumeric after that." in response.json()["detail"]

@pytest.mark.asyncio
async def test_bulk_download_unauthorized(client: AsyncClient):
    """Test bulk download without an API key."""
    request_data = BulkDownloadRequest(lan_ids=["LAN12345"])
    response = await client.post(
        "/api/v1/recordings/bulk-download",
        json=request_data.model_dump()
    )
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

@pytest.mark.asyncio
async def test_bulk_download_invalid_api_key(client: AsyncClient):
    """Test bulk download with an invalid API key."""
    request_data = BulkDownloadRequest(lan_ids=["LAN12345"])
    response = await client.post(
        "/api/v1/recordings/bulk-download",
        json=request_data.model_dump(),
        headers={"X-API-Key": "wrongkey"}
    )
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "connected"}

@pytest.mark.asyncio
async def test_rate_limiting(client: AsyncClient):
    """Test the rate limiting middleware."""
    # Temporarily set a very low rate limit for testing
    original_limit = settings.RATE_LIMIT_PER_MINUTE
    settings.RATE_LIMIT_PER_MINUTE = 2 # Allow 2 requests per minute for this test

    try:
        # Make requests within the limit
        for _ in range(2):
            response = await client.get("/health")
            assert response.status_code == 200
        
        # Make one more request to exceed the limit
        response = await client.get("/health")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
    finally:
        settings.RATE_LIMIT_PER_MINUTE = original_limit # Reset to original

@pytest.mark.asyncio
async def test_file_cleanup(client: AsyncClient, db_session: AsyncSession, mock_nfs_path: str):
    """Test that temporary zip files are cleaned up."""
    rec1 = Recording(lan_id="LAN12345", file_path="2023/01/LAN12345_recording.mp4", status=RecordingStatus.AVAILABLE)
    db_session.add(rec1)
    await db_session.commit()

    request_data = BulkDownloadRequest(lan_ids=["LAN12345"])
    response = await client.post(
        "/api/v1/recordings/bulk-download",
        json=request_data.model_dump(),
        headers={"X-API-Key": settings.API_KEY}
    )
    assert response.status_code == 200

    # The file should exist immediately after the response is sent
    # but should be cleaned up by the background task shortly after.
    # We need to give the background task a moment to run.
    # In a real test, you might mock BackgroundTasks or use a more robust way
    # to wait for background tasks to complete. For simplicity, a short sleep.
    await asyncio.sleep(0.1) 
    
    # Check if any zip files remain in the temp directory
    temp_files = os.listdir(settings.TEMP_ZIP_DIR)
    assert len(temp_files) == 0, f"Temporary files not cleaned up: {temp_files}"