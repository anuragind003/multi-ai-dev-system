import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
import os
import shutil
from datetime import date, datetime

from main import app
from database import get_db
from crud import VKYCCrud
from services import VKYCService, NFSClient, get_vkyc_service
from schemas import VKYCRecordResponse, VKYCSearchRequest, VKYCDownloadRequest
from models import VKYCRecord
from config import settings
from jose import jwt

# Create a test client
client = TestClient(app)

# Mock dependencies
@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock()

@pytest.fixture
def mock_crud(mock_db_session):
    """Mock VKYCCrud instance."""
    return AsyncMock(spec=VKYCCrud)

@pytest.fixture
def mock_nfs_client():
    """Mock NFSClient instance."""
    nfs_client = AsyncMock(spec=NFSClient)
    nfs_client.base_path = "./test_nfs_recordings" # Ensure base_path is set for mock
    return nfs_client

@pytest.fixture
def mock_vkyc_service(mock_crud, mock_nfs_client):
    """Mock VKYCService instance."""
    service = AsyncMock(spec=VKYCService)
    service.crud = mock_crud # Attach mock_crud to service
    service.nfs_client = mock_nfs_client # Attach mock_nfs_client to service
    return service

@pytest.fixture(autouse=True)
def override_dependencies(mock_db_session, mock_crud, mock_vkyc_service):
    """Override FastAPI dependencies with mocks."""
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[VKYCCrud] = lambda db=mock_db_session: mock_crud
    app.dependency_overrides[get_vkyc_service] = lambda crud=mock_crud: mock_vkyc_service
    
    # Mock get_current_user to always return a valid user for tests
    def mock_get_current_user():
        return "testuser"
    app.dependency_overrides[app.router.dependencies[0].dependency] = mock_get_current_user # This targets the global auth dependency

@pytest.fixture
def auth_token():
    """Generate a valid JWT token for testing."""
    to_encode = {"sub": "testuser"}
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

@pytest.fixture
def auth_headers(auth_token):
    """Headers with authorization token."""
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture
def sample_records_data():
    """Sample VKYCRecordResponse data for API responses."""
    return [
        VKYCRecordResponse(id=1, lan_id="LAN001", file_path="/path/to/LAN001.mp4", upload_date=datetime(2023, 1, 1), status="COMPLETED"),
        VKYCRecordResponse(id=2, lan_id="LAN002", file_path="/path/to/LAN002.mp4", upload_date=datetime(2023, 1, 2), status="COMPLETED"),
    ]

@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Service is healthy"}

@pytest.mark.asyncio
async def test_search_vkyc_records_success(mock_vkyc_service, sample_records_data, auth_headers):
    """Test successful search endpoint."""
    mock_vkyc_service.search_vkyc_records.return_value = (sample_records_data, 2)
    
    search_payload = {"page": 1, "page_size": 10}
    response = client.post("/api/v1/vkyc/search", json=search_payload, headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["total_records"] == 2
    assert len(response.json()["records"]) == 2
    assert response.json()["records"][0]["lan_id"] == "LAN001"
    mock_vkyc_service.search_vkyc_records.assert_called_once()

@pytest.mark.asyncio
async def test_search_vkyc_records_unauthorized(mock_vkyc_service):
    """Test search endpoint without authentication."""
    response = client.post("/api/v1/vkyc/search", json={"page": 1, "page_size": 10})
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
    mock_vkyc_service.search_vkyc_records.assert_not_called()

@pytest.mark.asyncio
async def test_search_vkyc_records_validation_error(mock_vkyc_service, auth_headers):
    """Test search endpoint with invalid input."""
    response = client.post("/api/v1/vkyc/search", json={"page_size": 0}, headers=auth_headers) # page_size must be >= 1
    assert response.status_code == 422
    assert "errors" in response.json()
    mock_vkyc_service.search_vkyc_records.assert_not_called()

@pytest.mark.asyncio
async def test_download_single_vkyc_record_success(mock_vkyc_service, auth_headers):
    """Test successful single download endpoint."""
    test_lan_id = "LAN001"
    test_file_path = "./test_nfs_recordings/LAN001.mp4"
    
    # Create a dummy file for the mock_nfs_client to "read"
    os.makedirs(os.path.dirname(test_file_path), exist_ok=True)
    with open(test_file_path, "wb") as f:
        f.write(b"dummy video content")

    mock_vkyc_service.download_single_vkyc_record.return_value = (test_file_path, test_lan_id)
    mock_vkyc_service.nfs_client.get_file_stream.return_value = iter([b"dummy video content"])
    mock_vkyc_service.nfs_client.get_file_size.return_value = len(b"dummy video content")

    response = client.get(f"/api/v1/vkyc/download/{test_lan_id}", headers=auth_headers)
    
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "video/mp4"
    assert response.headers["Content-Disposition"] == f"attachment; filename={test_lan_id}.mp4"
    assert response.content == b"dummy video content"
    mock_vkyc_service.download_single_vkyc_record.assert_called_once_with(test_lan_id)
    mock_vkyc_service.nfs_client.get_file_stream.assert_called_once_with(test_file_path)
    mock_vkyc_service.nfs_client.get_file_size.assert_called_once_with(test_file_path)
    
    os.remove(test_file_path) # Clean up dummy file

@pytest.mark.asyncio
async def test_download_single_vkyc_record_not_found(mock_vkyc_service, auth_headers):
    """Test single download when record not found."""
    mock_vkyc_service.download_single_vkyc_record.side_effect = NotFoundException("Record not found.")
    
    response = client.get("/api/v1/vkyc/download/NONEXISTENT", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Record not found."

@pytest.mark.asyncio
async def test_download_bulk_vkyc_records_success(mock_vkyc_service, auth_headers):
    """Test successful bulk download endpoint."""
    test_lan_ids = ["LAN001", "LAN002"]
    test_zip_path = "./temp_downloads/test_bulk.zip"
    
    # Create a dummy zip file for the service to "return"
    os.makedirs(os.path.dirname(test_zip_path), exist_ok=True)
    with open(test_zip_path, "wb") as f:
        f.write(b"dummy zip content")

    mock_vkyc_service.download_bulk_vkyc_records.return_value = test_zip_path
    
    response = client.post("/api/v1/vkyc/download/bulk", json={"lan_ids": test_lan_ids}, headers=auth_headers)
    
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/zip"
    assert response.headers["Content-Disposition"].startswith("attachment; filename=")
    assert response.content == b"dummy zip content"
    mock_vkyc_service.download_bulk_vkyc_records.assert_called_once_with(test_lan_ids)
    
    # Ensure the background task to delete the file is added (though not executed in test client)
    # In a real test, you'd check if the file is eventually removed.
    # For now, we manually clean up.
    if os.path.exists(test_zip_path):
        os.remove(test_zip_path)

@pytest.mark.asyncio
async def test_download_bulk_vkyc_records_too_many_ids(mock_vkyc_service, auth_headers):
    """Test bulk download with too many LAN IDs."""
    test_lan_ids = [f"LAN{i:03d}" for i in range(1, 12)] # 11 IDs
    
    response = client.post("/api/v1/vkyc/download/bulk", json={"lan_ids": test_lan_ids}, headers=auth_headers)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Maximum 10 LAN IDs allowed for bulk download."
    mock_vkyc_service.download_bulk_vkyc_records.assert_not_called()

@pytest.mark.asyncio
async def test_download_bulk_vkyc_records_service_error(mock_vkyc_service, auth_headers):
    """Test bulk download when service layer fails."""
    mock_vkyc_service.download_bulk_vkyc_records.side_effect = FileOperationException("Failed to create zip.")
    
    response = client.post("/api/v1/vkyc/download/bulk", json={"lan_ids": ["LAN001"]}, headers=auth_headers)
    
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to create zip."

@pytest.mark.asyncio
async def test_login_for_access_token_success(mock_vkyc_service):
    """Test successful login endpoint."""
    mock_vkyc_service.authenticate_user.return_value = MagicMock(access_token="fake_token", token_type="bearer")
    
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "testuser", "password": "password123"}
    )
    
    assert response.status_code == 200
    assert response.json()["access_token"] == "fake_token"
    assert response.json()["token_type"] == "bearer"
    mock_vkyc_service.authenticate_user.assert_called_once()

@pytest.mark.asyncio
async def test_login_for_access_token_invalid_credentials(mock_vkyc_service):
    """Test login with invalid credentials."""
    mock_vkyc_service.authenticate_user.return_value = None # Simulate authentication failure
    
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "testuser", "password": "wrongpassword"}
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password."

@pytest.mark.asyncio
async def test_security_headers():
    """Test if security headers are present in a response."""
    response = client.get("/health") # Any endpoint will do
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers # Will be present if running with HTTPS, otherwise not
    assert response.headers["X-Frame-Options"] == settings.X_FRAME_OPTIONS
    assert response.headers["X-Content-Type-Options"] == settings.X_CONTENT_TYPE_OPTIONS
    assert response.headers["Referrer-Policy"] == settings.REFERRER_POLICY
    assert response.headers["X-XSS-Protection"] == "1; mode=block"