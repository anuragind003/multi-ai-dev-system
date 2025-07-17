import pytest
import os
import shutil
from unittest.mock import AsyncMock, MagicMock
from datetime import date, datetime, timedelta

from services import VKYCService, NFSClient
from crud import VKYCCrud
from schemas import VKYCSearchRequest, VKYCRecordResponse, VKYCRecordCreate
from models import VKYCRecord
from utils.exceptions import NotFoundException, FileOperationException, ServiceException, CustomValidationException

# Mock NFS_BASE_PATH for testing
TEST_NFS_BASE_PATH = "./test_nfs_recordings"

@pytest.fixture(autouse=True)
def setup_teardown_nfs_path():
    """Fixture to create and clean up the test NFS directory."""
    if os.path.exists(TEST_NFS_BASE_PATH):
        shutil.rmtree(TEST_NFS_BASE_PATH)
    os.makedirs(TEST_NFS_BASE_PATH, exist_ok=True)
    yield
    if os.path.exists(TEST_NFS_BASE_PATH):
        shutil.rmtree(TEST_NFS_BASE_PATH)

@pytest.fixture
def mock_crud():
    """Mock VKYCCrud instance."""
    return AsyncMock(spec=VKYCCrud)

@pytest.fixture
def mock_nfs_client():
    """Mock NFSClient instance."""
    nfs_client = AsyncMock(spec=NFSClient)
    nfs_client.base_path = TEST_NFS_BASE_PATH # Ensure base_path is set for mock
    return nfs_client

@pytest.fixture
def vkyc_service(mock_crud, mock_nfs_client):
    """VKYCService instance with mocked dependencies."""
    return VKYCService(crud=mock_crud, nfs_client=mock_nfs_client)

@pytest.fixture
def sample_records():
    """Sample VKYCRecord objects for testing."""
    return [
        VKYCRecord(id=1, lan_id="LAN001", file_path=os.path.join(TEST_NFS_BASE_PATH, "LAN001.mp4"), upload_date=datetime(2023, 1, 1), status="COMPLETED", duration_seconds=60, file_size_bytes=1000, agent_id="A001", customer_name="Alice"),
        VKYCRecord(id=2, lan_id="LAN002", file_path=os.path.join(TEST_NFS_BASE_PATH, "LAN002.mp4"), upload_date=datetime(2023, 1, 2), status="COMPLETED", duration_seconds=90, file_size_bytes=1500, agent_id="A002", customer_name="Bob"),
        VKYCRecord(id=3, lan_id="LAN003", file_path=os.path.join(TEST_NFS_BASE_PATH, "LAN003.mp4"), upload_date=datetime(2023, 1, 3), status="FAILED", duration_seconds=30, file_size_bytes=500, agent_id="A001", customer_name="Charlie"),
    ]

@pytest.mark.asyncio
async def test_search_vkyc_records_success(vkyc_service, mock_crud, sample_records):
    """Test successful search of VKYC records."""
    mock_crud.search_records.return_value = (sample_records, len(sample_records))
    search_params = VKYCSearchRequest(page=1, page_size=10)

    records, total = await vkyc_service.search_vkyc_records(search_params)

    mock_crud.search_records.assert_called_once_with(search_params)
    assert len(records) == len(sample_records)
    assert total == len(sample_records)
    assert all(isinstance(r, VKYCRecordResponse) for r in records)
    assert records[0].lan_id == "LAN001"

@pytest.mark.asyncio
async def test_search_vkyc_records_no_results(vkyc_service, mock_crud):
    """Test search with no matching records."""
    mock_crud.search_records.return_value = ([], 0)
    search_params = VKYCSearchRequest(lan_id="NONEXISTENT")

    records, total = await vkyc_service.search_vkyc_records(search_params)

    assert len(records) == 0
    assert total == 0

@pytest.mark.asyncio
async def test_search_vkyc_records_crud_error(vkyc_service, mock_crud):
    """Test search when CRUD operation fails."""
    mock_crud.search_records.side_effect = ServiceException("DB error")
    search_params = VKYCSearchRequest()

    with pytest.raises(ServiceException, match="DB error"):
        await vkyc_service.search_vkyc_records(search_params)

@pytest.mark.asyncio
async def test_download_single_vkyc_record_success(vkyc_service, mock_crud, mock_nfs_client, sample_records):
    """Test successful single record download."""
    record = sample_records[0]
    mock_crud.get_record_by_lan_id.return_value = record
    mock_nfs_client.file_exists.return_value = True
    
    # Create a dummy file for the mock_nfs_client to "read"
    os.makedirs(os.path.dirname(record.file_path), exist_ok=True)
    with open(record.file_path, "wb") as f:
        f.write(b"dummy video content")
    
    file_path, filename = await vkyc_service.download_single_vkyc_record(record.lan_id)

    mock_crud.get_record_by_lan_id.assert_called_once_with(record.lan_id)
    mock_nfs_client.file_exists.assert_called_once_with(record.file_path)
    assert file_path == record.file_path
    assert filename == record.lan_id

@pytest.mark.asyncio
async def test_download_single_vkyc_record_not_found_db(vkyc_service, mock_crud):
    """Test single record download when record not found in DB."""
    mock_crud.get_record_by_lan_id.return_value = None

    with pytest.raises(NotFoundException, match="VKYC record with LAN ID 'LAN004' not found."):
        await vkyc_service.download_single_vkyc_record("LAN004")

@pytest.mark.asyncio
async def test_download_single_vkyc_record_file_not_found_nfs(vkyc_service, mock_crud, mock_nfs_client, sample_records):
    """Test single record download when file not found on NFS."""
    record = sample_records[0]
    mock_crud.get_record_by_lan_id.return_value = record
    mock_nfs_client.file_exists.return_value = False # Simulate file not existing

    with pytest.raises(FileOperationException, match="Recording file for LAN ID 'LAN001' not found on server."):
        await vkyc_service.download_single_vkyc_record(record.lan_id)

@pytest.mark.asyncio
async def test_download_bulk_vkyc_records_success(vkyc_service, mock_crud, mock_nfs_client, sample_records):
    """Test successful bulk record download."""
    lan_ids = ["LAN001", "LAN002"]
    mock_crud.get_record_by_lan_id.side_effect = lambda lan_id: next((r for r in sample_records if r.lan_id == lan_id), None)
    mock_nfs_client.file_exists.return_value = True
    
    # Create dummy files for the mock_nfs_client to "read"
    for record in sample_records:
        os.makedirs(os.path.dirname(record.file_path), exist_ok=True)
        with open(record.file_path, "wb") as f:
            f.write(b"dummy content for " + record.lan_id.encode())

    zip_file_path = await vkyc_service.download_bulk_vkyc_records(lan_ids)

    assert os.path.exists(zip_file_path)
    assert zip_file_path.endswith(".zip")

    # Verify contents of the zip file
    with zipfile.ZipFile(zip_file_path, 'r') as zf:
        assert f"LAN001_{os.path.basename(sample_records[0].file_path)}" in zf.namelist()
        assert f"LAN002_{os.path.basename(sample_records[1].file_path)}" in zf.namelist()
        assert len(zf.namelist()) == 2 # Only 2 files should be in the zip

    os.remove(zip_file_path) # Clean up

@pytest.mark.asyncio
async def test_download_bulk_vkyc_records_partial_success(vkyc_service, mock_crud, mock_nfs_client, sample_records):
    """Test bulk download with some files failing."""
    lan_ids = ["LAN001", "LAN004", "LAN003"] # LAN004 doesn't exist, LAN003 exists but file might not
    
    # Mock DB returns for LAN001 and LAN003, but not LAN004
    mock_crud.get_record_by_lan_id.side_effect = lambda lan_id: {
        "LAN001": sample_records[0],
        "LAN003": sample_records[2]
    }.get(lan_id)

    # Mock NFS client: LAN001 exists, LAN003 does not
    mock_nfs_client.file_exists.side_effect = lambda path: path == sample_records[0].file_path
    
    # Create dummy file for LAN001
    os.makedirs(os.path.dirname(sample_records[0].file_path), exist_ok=True)
    with open(sample_records[0].file_path, "wb") as f:
        f.write(b"dummy content for LAN001")

    zip_file_path = await vkyc_service.download_bulk_vkyc_records(lan_ids)

    assert os.path.exists(zip_file_path)
    with zipfile.ZipFile(zip_file_path, 'r') as zf:
        assert f"LAN001_{os.path.basename(sample_records[0].file_path)}" in zf.namelist()
        assert "download_report.txt" in zf.namelist() # Should contain a report for failures
        assert len(zf.namelist()) == 2 # One successful file + report

        report_content = zf.read("download_report.txt").decode()
        assert "Successfully downloaded: LAN001" in report_content
        assert "Failed to download: LAN004 (Not found in database), LAN003 (File not found on server)" in report_content

    os.remove(zip_file_path) # Clean up

@pytest.mark.asyncio
async def test_download_bulk_vkyc_records_no_files_downloaded(vkyc_service, mock_crud, mock_nfs_client):
    """Test bulk download when no files can be downloaded."""
    lan_ids = ["LAN_FAIL1", "LAN_FAIL2"]
    mock_crud.get_record_by_lan_id.return_value = None # Simulate no records in DB
    mock_nfs_client.file_exists.return_value = False

    with pytest.raises(FileOperationException, match="No files could be downloaded."):
        await vkyc_service.download_bulk_vkyc_records(lan_ids)
    
    # Ensure no zip file was created or it was cleaned up
    assert not any(f.startswith("vkyc_records_") and f.endswith(".zip") for f in os.listdir("./temp_downloads"))

@pytest.mark.asyncio
async def test_download_bulk_vkyc_records_too_many_ids(vkyc_service):
    """Test bulk download with more than 10 LAN IDs."""
    lan_ids = [f"LAN{i:03d}" for i in range(1, 12)] # 11 IDs

    with pytest.raises(CustomValidationException, match="Maximum 10 LAN IDs allowed for bulk download."):
        await vkyc_service.download_bulk_vkyc_records(lan_ids)

@pytest.mark.asyncio
async def test_authenticate_user_success(vkyc_service):
    """Test successful user authentication."""
    user_login = UserLogin(username="testuser", password="password123")
    token = await vkyc_service.authenticate_user(user_login)
    assert token is not None
    assert token.access_token is not None
    assert token.token_type == "bearer"

@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(vkyc_service):
    """Test user authentication with invalid password."""
    user_login = UserLogin(username="testuser", password="wrongpassword")
    with pytest.raises(UnauthorizedException, match="Incorrect username or password."):
        await vkyc_service.authenticate_user(user_login)

@pytest.mark.asyncio
async def test_authenticate_user_non_existent_user(vkyc_service):
    """Test user authentication with non-existent user."""
    user_login = UserLogin(username="nonexistent", password="password123")
    with pytest.raises(UnauthorizedException, match="Incorrect username or password."):
        await vkyc_service.authenticate_user(user_login)