import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from io import StringIO

from sqlalchemy.orm import Session

from app.services.vkyc_recording_service import VKYCRecordingService
from app.schemas.vkyc_recording import VKYCRecordingCreate, VKYCRecordingUpdate, CSVUploadResult
from app.models.vkyc_recording import VKYCRecording
from app.core.exceptions import NotFoundException, ConflictException, UnprocessableEntityException, InternalServerErrorException

# Mock database session for testing
@pytest.fixture
def mock_db_session():
    """Provides a mock SQLAlchemy session."""
    return MagicMock(spec=Session)

@pytest.fixture
def vkyc_service(mock_db_session):
    """Provides an instance of VKYCRecordingService with a mock DB session."""
    return VKYCRecordingService(mock_db_session)

@pytest.fixture
def sample_recording_data():
    """Provides sample VKYC recording data."""
    return VKYCRecordingCreate(
        lan_id="LAN12345",
        recording_date=datetime(2023, 1, 15, 10, 30, 0),
        file_path="/nfs/vkyc/recordings/LAN12345.mp4",
        status="PENDING"
    )

@pytest.fixture
def sample_db_recording(sample_recording_data):
    """Provides a sample VKYCRecording ORM object."""
    return VKYCRecording(
        id=1,
        uploaded_by="test_user",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        **sample_recording_data.model_dump()
    )

# --- Test create_recording ---
def test_create_recording_success(vkyc_service, mock_db_session, sample_recording_data):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None # No existing record
    
    result = vkyc_service.create_recording(sample_recording_data, "test_user")
    
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()
    assert result.lan_id == sample_recording_data.lan_id

def test_create_recording_conflict(vkyc_service, mock_db_session, sample_recording_data, sample_db_recording):
    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_db_recording # Record exists
    
    with pytest.raises(ConflictException):
        vkyc_service.create_recording(sample_recording_data, "test_user")
    
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

def test_create_recording_db_error(vkyc_service, mock_db_session, sample_recording_data):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    mock_db_session.add.side_effect = Exception("DB connection lost")
    
    with pytest.raises(InternalServerErrorException):
        vkyc_service.create_recording(sample_recording_data, "test_user")
    
    mock_db_session.rollback.assert_called_once()

# --- Test get_recording_by_id ---
def test_get_recording_by_id_success(vkyc_service, mock_db_session, sample_db_recording):
    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_db_recording
    
    result = vkyc_service.get_recording_by_id(1)
    
    assert result.id == 1
    assert result.lan_id == sample_db_recording.lan_id

def test_get_recording_by_id_not_found(vkyc_service, mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    with pytest.raises(NotFoundException):
        vkyc_service.get_recording_by_id(999)

# --- Test get_recordings ---
def test_get_recordings_no_filters(vkyc_service, mock_db_session, sample_db_recording):
    mock_db_session.query.return_value.filter.return_value.count.return_value = 1
    mock_db_session.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [sample_db_recording]
    
    records, total = vkyc_service.get_recordings()
    
    assert total == 1
    assert len(records) == 1
    assert records[0].lan_id == sample_db_recording.lan_id

def test_get_recordings_with_filters(vkyc_service, mock_db_session, sample_db_recording):
    mock_db_session.query.return_value.filter.return_value.filter.return_value.count.return_value = 1
    mock_db_session.query.return_value.filter.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [sample_db_recording]
    
    records, total = vkyc_service.get_recordings(lan_id="LAN123", status="PENDING")
    
    assert total == 1
    assert len(records) == 1

# --- Test update_recording ---
def test_update_recording_success(vkyc_service, mock_db_session, sample_db_recording):
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [sample_db_recording, None] # First call finds, second for LAN ID check finds nothing
    
    update_data = VKYCRecordingUpdate(status="PROCESSED")
    result = vkyc_service.update_recording(1, update_data)
    
    mock_db_session.add.assert_called_once_with(sample_db_recording)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(sample_db_recording)
    assert result.status == "PROCESSED"

def test_update_recording_not_found(vkyc_service, mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    update_data = VKYCRecordingUpdate(status="PROCESSED")
    with pytest.raises(NotFoundException):
        vkyc_service.update_recording(999, update_data)

def test_update_recording_lan_id_conflict(vkyc_service, mock_db_session, sample_db_recording):
    existing_other_record = VKYCRecording(id=2, lan_id="LAN99999", recording_date=datetime.now(), file_path="path", status="PENDING", uploaded_by="user")
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [sample_db_recording, existing_other_record] # First call finds original, second finds conflicting LAN ID
    
    update_data = VKYCRecordingUpdate(lan_id="LAN99999")
    with pytest.raises(ConflictException):
        vkyc_service.update_recording(1, update_data)

# --- Test delete_recording ---
def test_delete_recording_success(vkyc_service, mock_db_session, sample_db_recording):
    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_db_recording
    
    vkyc_service.delete_recording(1)
    
    mock_db_session.delete.assert_called_once_with(sample_db_recording)
    mock_db_session.commit.assert_called_once()

def test_delete_recording_not_found(vkyc_service, mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    with pytest.raises(NotFoundException):
        vkyc_service.delete_recording(999)

# --- Test ingest_csv_data ---
def test_ingest_csv_data_success_new_records(vkyc_service, mock_db_session):
    csv_content = b"lan_id,recording_date,file_path,status\nLAN001,2023-01-01 10:00:00,/path/001.mp4,PENDING\nLAN002,2023-01-02 11:00:00,/path/002.mp4,PROCESSED"
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = None # No existing records
    
    result = vkyc_service.ingest_csv_data(csv_content, "csv_uploader")
    
    assert result.total_records == 2
    assert result.successful_ingestions == 2
    assert result.failed_ingestions == 0
    assert len(result.errors) == 0
    assert mock_db_session.add.call_count == 2
    assert mock_db_session.commit.call_count == 1

def test_ingest_csv_data_success_mixed_records(vkyc_service, mock_db_session):
    csv_content = b"lan_id,recording_date,file_path,status\nLAN001,2023-01-01 10:00:00,/path/001.mp4,PENDING\nLAN002,2023-01-02 11:00:00,/path/002.mp4,PROCESSED"
    
    # Mock one record as existing, one as new
    existing_record = VKYCRecording(id=1, lan_id="LAN001", recording_date=datetime(2022,1,1), file_path="/old/path.mp4", status="OLD", uploaded_by="old_user")
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [existing_record, None] # First LAN001 exists, LAN002 does not
    
    result = vkyc_service.ingest_csv_data(csv_content, "csv_uploader")
    
    assert result.total_records == 2
    assert result.successful_ingestions == 2
    assert result.failed_ingestions == 0
    assert len(result.errors) == 0
    assert mock_db_session.add.call_count == 2 # One for update, one for new
    assert mock_db_session.commit.call_count == 1
    assert existing_record.status == "PENDING" # Check if existing record was updated

def test_ingest_csv_data_with_errors(vkyc_service, mock_db_session):
    csv_content = b"lan_id,recording_date,file_path,status\nLAN001,INVALID_DATE,/path/001.mp4,PENDING\nLAN002,2023-01-02 11:00:00,/path/002.mp4,PROCESSED"
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    result = vkyc_service.ingest_csv_data(csv_content, "csv_uploader")
    
    assert result.total_records == 2
    assert result.successful_ingestions == 1
    assert result.failed_ingestions == 1
    assert len(result.errors) == 1
    assert "Row 2: Invalid recording_date format" in result.errors[0]
    assert mock_db_session.add.call_count == 1 # Only one successful record added
    assert mock_db_session.commit.call_count == 1

def test_ingest_csv_data_empty_file(vkyc_service, mock_db_session):
    csv_content = b"lan_id,recording_date,file_path,status\n"
    
    with pytest.raises(UnprocessableEntityException, match="CSV file is empty or contains only headers."):
        vkyc_service.ingest_csv_data(csv_content, "csv_uploader")
    
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

def test_ingest_csv_data_missing_headers(vkyc_service, mock_db_session):
    csv_content = b"lan_id,file_path,status\nLAN001,2023-01-01 10:00:00,/path/001.mp4,PENDING" # Missing recording_date
    
    with pytest.raises(UnprocessableEntityException, match="Missing required CSV headers: recording_date."):
        vkyc_service.ingest_csv_data(csv_content, "csv_uploader")
    
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

def test_ingest_csv_data_db_transaction_failure(vkyc_service, mock_db_session):
    csv_content = b"lan_id,recording_date,file_path,status\nLAN001,2023-01-01 10:00:00,/path/001.mp4,PENDING"
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    mock_db_session.commit.side_effect = Exception("Database commit failed")
    
    with pytest.raises(InternalServerErrorException, match="Failed to ingest CSV data due to a database transaction error."):
        vkyc_service.ingest_csv_data(csv_content, "csv_uploader")
    
    mock_db_session.rollback.assert_called_once()
    assert mock_db_session.add.call_count == 1 # Add was called before commit failed