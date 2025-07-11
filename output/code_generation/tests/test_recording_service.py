import pytest
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models import Recording, RecordingStatus
from services.recording_service import RecordingService
from core.exceptions import RecordingNotFoundException, BulkDownloadFailedException, InvalidInputException
from config import settings

# --- Fixtures ---

@pytest.fixture(scope="module")
def temp_nfs_path():
    """Fixture to create a temporary directory simulating an NFS share."""
    temp_dir = tempfile.mkdtemp(prefix="test_nfs_")
    # Create some dummy files
    os.makedirs(os.path.join(temp_dir, "2023", "01"), exist_ok=True)
    with open(os.path.join(temp_dir, "2023", "01", "rec_123.mp4"), "w") as f:
        f.write("dummy video content 1")
    with open(os.path.join(temp_dir, "2023", "01", "rec_456.mp4"), "w") as f:
        f.write("dummy video content 2")
    with open(os.path.join(temp_dir, "2023", "01", "rec_789.mp4"), "w") as f:
        f.write("dummy video content 3")
    
    # Patch the NFS_RECORDINGS_BASE_PATH in settings
    original_nfs_path = settings.NFS_RECORDINGS_BASE_PATH
    settings.NFS_RECORDINGS_BASE_PATH = temp_dir
    
    yield temp_dir
    
    # Clean up
    settings.NFS_RECORDINGS_BASE_PATH = original_nfs_path # Restore original path
    shutil.rmtree(temp_dir)

@pytest.fixture(scope="module")
def temp_download_dir():
    """Fixture to create a temporary directory for downloads."""
    temp_dir = tempfile.mkdtemp(prefix="test_downloads_")
    
    # Patch the TEMP_DOWNLOAD_DIR in settings
    original_download_dir = settings.TEMP_DOWNLOAD_DIR
    settings.TEMP_DOWNLOAD_DIR = temp_dir
    
    yield temp_dir
    
    # Clean up
    settings.TEMP_DOWNLOAD_DIR = original_download_dir # Restore original path
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_db_session():
    """Fixture to provide a mock SQLAlchemy session."""
    session = MagicMock(spec=Session)
    yield session
    session.reset_mock()

@pytest.fixture
def recording_data():
    """Fixture for sample recording data."""
    return [
        Recording(id=1, lan_id="LAN001", file_path="2023/01/rec_123.mp4", recorded_at=datetime.now(), status=RecordingStatus.AVAILABLE),
        Recording(id=2, lan_id="LAN002", file_path="2023/01/rec_456.mp4", recorded_at=datetime.now(), status=RecordingStatus.AVAILABLE),
        Recording(id=3, lan_id="LAN003", file_path="2023/01/rec_789.mp4", recorded_at=datetime.now(), status=RecordingStatus.AVAILABLE),
        Recording(id=4, lan_id="LAN004", file_path="non_existent.mp4", recorded_at=datetime.now(), status=RecordingStatus.AVAILABLE),
        Recording(id=5, lan_id="LAN005", file_path="2023/01/rec_999.mp4", recorded_at=datetime.now(), status=RecordingStatus.PROCESSING), # Not available
    ]

# --- Tests for get_recording_by_lan_id ---

def test_get_recording_by_lan_id_success(mock_db_session, recording_data):
    """Test successful retrieval of a single recording."""
    mock_db_session.query.return_value.filter.return_value.first.return_value = recording_data[0]
    service = RecordingService(mock_db_session)
    
    result = service.get_recording_by_lan_id("LAN001")
    assert result.lan_id == "LAN001"
    assert mock_db_session.query.called
    assert mock_db_session.query.return_value.filter.called

def test_get_recording_by_lan_id_not_found(mock_db_session):
    """Test case where recording is not found."""
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    service = RecordingService(mock_db_session)
    
    with pytest.raises(RecordingNotFoundException) as exc_info:
        service.get_recording_by_lan_id("NONEXISTENT")
    assert "not found or not available" in str(exc_info.value.detail)

def test_get_recording_by_lan_id_not_available(mock_db_session, recording_data):
    """Test case where recording is found but not available (e.g., PROCESSING status)."""
    # Simulate DB returning None because of status filter
    mock_db_session.query.return_value.filter.return_value.first.return_value = None 
    service = RecordingService(mock_db_session)
    
    with pytest.raises(RecordingNotFoundException) as exc_info:
        service.get_recording_by_lan_id("LAN005") # This one is PROCESSING
    assert "not found or not available" in str(exc_info.value.detail)

# --- Tests for get_recordings_by_lan_ids ---

def test_get_recordings_by_lan_ids_success(mock_db_session, recording_data):
    """Test successful retrieval of multiple recordings."""
    mock_db_session.query.return_value.filter.return_value.all.return_value = [recording_data[0], recording_data[1]]
    service = RecordingService(mock_db_session)
    
    lan_ids = ["LAN001", "LAN002"]
    result = service.get_recordings_by_lan_ids(lan_ids)
    assert len(result) == 2
    assert {r.lan_id for r in result} == set(lan_ids)

def test_get_recordings_by_lan_ids_some_not_found(mock_db_session, recording_data):
    """Test case where some requested recordings are not found."""
    # Simulate only LAN001 being returned by DB
    mock_db_session.query.return_value.filter.return_value.all.return_value = [recording_data[0]]
    service = RecordingService(mock_db_session)
    
    lan_ids = ["LAN001", "LAN006"] # LAN006 is missing
    with pytest.raises(RecordingNotFoundException) as exc_info:
        service.get_recordings_by_lan_ids(lan_ids)
    assert "LAN006" in str(exc_info.value.detail)

def test_get_recordings_by_lan_ids_empty_list(mock_db_session):
    """Test with an empty list of LAN IDs."""
    service = RecordingService(mock_db_session)
    with pytest.raises(InvalidInputException) as exc_info:
        service.get_recordings_by_lan_ids([])
    assert "cannot be empty" in str(exc_info.value.detail)

def test_get_recordings_by_lan_ids_too_many_records(mock_db_session):
    """Test with more than the allowed number of records."""
    service = RecordingService(mock_db_session)
    lan_ids = [f"LAN{i}" for i in range(settings.MAX_BULK_DOWNLOAD_RECORDS + 1)]
    with pytest.raises(InvalidInputException) as exc_info:
        service.get_recordings_by_lan_ids(lan_ids)
    assert "Maximum 10 recordings allowed" in str(exc_info.value.detail)

def test_get_recordings_by_lan_ids_db_error(mock_db_session):
    """Test database error during retrieval."""
    mock_db_session.query.return_value.filter.return_value.all.side_effect = SQLAlchemyError("DB connection lost")
    service = RecordingService(mock_db_session)
    
    with pytest.raises(BulkDownloadFailedException) as exc_info:
        service.get_recordings_by_lan_ids(["LAN001"])
    assert "Failed to retrieve recordings from database" in str(exc_info.value.detail)

# --- Tests for create_bulk_download_zip ---

@pytest.mark.asyncio
async def test_create_bulk_download_zip_success(mock_db_session, recording_data, temp_nfs_path, temp_download_dir):
    """Test successful ZIP creation."""
    service = RecordingService(mock_db_session)
    
    # Use recordings that have corresponding files in temp_nfs_path
    recordings_to_zip = [recording_data[0], recording_data[1]] 
    
    zip_path = await service.create_bulk_download_zip(recordings_to_zip)
    
    assert os.path.exists(zip_path)
    assert zip_path.startswith(temp_download_dir)
    assert zip_path.endswith(".zip")
    
    # Verify contents of the zip file
    with zipfile.ZipFile(zip_path, 'r') as zf:
        namelist = zf.namelist()
        assert f"{recordings_to_zip[0].lan_id}_{os.path.basename(recordings_to_zip[0].file_path)}" in namelist
        assert f"{recordings_to_zip[1].lan_id}_{os.path.basename(recordings_to_zip[1].file_path)}" in namelist
        assert len(namelist) == len(recordings_to_zip)
    
    # Clean up the created zip file
    os.remove(zip_path)

@pytest.mark.asyncio
async def test_create_bulk_download_zip_file_not_found_on_nfs(mock_db_session, recording_data, temp_nfs_path, temp_download_dir):
    """Test case where a recording file is not found on NFS."""
    service = RecordingService(mock_db_session)
    
    # Use recording_data[3] which has a non_existent.mp4 file_path
    recordings_to_zip = [recording_data[0], recording_data[3]] 
    
    with pytest.raises(BulkDownloadFailedException) as exc_info:
        await service.create_bulk_download_zip(recordings_to_zip)
    
    assert "Recording file not found" in str(exc_info.value.detail)
    # Ensure no partial zip file is left behind
    assert not any(f.endswith(".zip") for f in os.listdir(temp_download_dir))

@pytest.mark.asyncio
async def test_create_bulk_download_zip_empty_recordings_list(mock_db_session):
    """Test with an empty list of recordings."""
    service = RecordingService(mock_db_session)
    with pytest.raises(InvalidInputException) as exc_info:
        await service.create_bulk_download_zip([])
    assert "No recordings provided" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_create_bulk_download_zip_io_error(mock_db_session, recording_data, temp_nfs_path, temp_download_dir):
    """Test IO error during ZIP creation (e.g., disk full, permissions)."""
    service = RecordingService(mock_db_session)
    recordings_to_zip = [recording_data[0]]

    # Mock zipfile.ZipFile to raise an IOError
    with patch('zipfile.ZipFile') as mock_zipfile_class:
        mock_zipfile_class.side_effect = IOError("Disk full error")
        with pytest.raises(BulkDownloadFailedException) as exc_info:
            await service.create_bulk_download_zip(recordings_to_zip)
        assert "Failed to create ZIP archive" in str(exc_info.value.detail)
    
    # Ensure no partial zip file is left behind
    assert not any(f.endswith(".zip") for f in os.listdir(temp_download_dir))

@pytest.mark.asyncio
async def test_create_bulk_download_zip_size_limit_exceeded(mock_db_session, recording_data, temp_nfs_path, temp_download_dir):
    """Test when total size of recordings exceeds the configured limit."""
    service = RecordingService(mock_db_session)
    
    # Temporarily reduce the max download size for this test
    original_max_size = settings.MAX_BULK_DOWNLOAD_SIZE_MB
    settings.MAX_BULK_DOWNLOAD_SIZE_MB = 0.000001 # Very small limit (e.g., 1 byte)
    
    recordings_to_zip = [recording_data[0]] # This file has content, so it will exceed 1 byte
    
    with pytest.raises(BulkDownloadFailedException) as exc_info:
        await service.create_bulk_download_zip(recordings_to_zip)
    
    assert "Total size of recordings exceeds the limit" in str(exc_info.value.detail)
    
    # Restore original setting
    settings.MAX_BULK_DOWNLOAD_SIZE_MB = original_max_size
    
    # Ensure no partial zip file is left behind
    assert not any(f.endswith(".zip") for f in os.listdir(temp_download_dir))