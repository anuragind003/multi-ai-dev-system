### FILE: app/tests/test_audit_log_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.services.audit_log_service import AuditLogService
from app.schemas.audit_log import AuditLogCreate, BulkDownloadRequest, BulkDownloadResult
from app.core.exceptions import InvalidInputException, ServiceUnavailableException
from app.models.audit_log import AuditLog

# Mock the NFSFileHandler
@pytest.fixture
def mock_nfs_file_handler():
    mock = AsyncMock()
    # Configure default behavior for check_file_exists
    mock.check_file_exists.side_effect = lambda lan_id: lan_id.startswith("LAN") and lan_id != "LAN_NOT_FOUND"
    # Configure default behavior for get_file_path
    mock.get_file_path.side_effect = lambda lan_id: f"/mnt/vkyc_recordings/2023/XX/{lan_id}.mp4" if lan_id.startswith("LAN") and lan_id != "LAN_NOT_FOUND" else None
    return mock

# Mock the AsyncSession
@pytest.fixture
def mock_db_session():
    mock = AsyncMock(spec=AsyncSession)
    mock.add = MagicMock()
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    mock.rollback = AsyncMock()
    mock.execute = AsyncMock()
    return mock

# Fixture for AuditLogService with mocked dependencies
@pytest.fixture
def audit_log_service(mock_db_session, mock_nfs_file_handler):
    return AuditLogService(db_session=mock_db_session, file_handler=mock_nfs_file_handler)

@pytest.mark.asyncio
async def test_create_log_success(audit_log_service, mock_db_session):
    log_data = AuditLogCreate(
        user_id="test_user",
        action="TEST_ACTION",
        resource_type="TEST_RESOURCE",
        resource_id="123",
        details={"key": "value"}
    )
    # Mock the refresh to return a valid AuditLog instance
    mock_db_session.refresh.side_effect = lambda obj: setattr(obj, 'id', 1) or setattr(obj, 'timestamp', datetime.now(timezone.utc))

    response = await audit_log_service.create_log(log_data)

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()
    assert response.user_id == "test_user"
    assert response.action == "TEST_ACTION"
    assert response.id == 1

@pytest.mark.asyncio
async def test_create_log_db_error(audit_log_service, mock_db_session):
    log_data = AuditLogCreate(
        user_id="test_user",
        action="TEST_ACTION",
        resource_type="TEST_RESOURCE",
        resource_id="123",
        details={"key": "value"}
    )
    mock_db_session.commit.side_effect = Exception("DB error")

    with pytest.raises(ServiceUnavailableException, match="Failed to record audit log"):
        await audit_log_service.create_log(log_data)

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_get_logs_success(audit_log_service, mock_db_session):
    # Mock the execute result
    mock_log_1 = AuditLog(id=1, user_id="user1", action="LOGIN", resource_type="USER", timestamp=datetime.now(timezone.utc))
    mock_log_2 = AuditLog(id=2, user_id="user2", action="BULK_DOWNLOAD", resource_type="RECORDING_BATCH", timestamp=datetime.now(timezone.utc))
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [mock_log_1, mock_log_2]

    logs = await audit_log_service.get_logs(limit=2)

    mock_db_session.execute.assert_called_once()
    assert len(logs) == 2
    assert logs[0].user_id == "user1"
    assert logs[1].action == "BULK_DOWNLOAD"

@pytest.mark.asyncio
async def test_record_bulk_download_success(audit_log_service, mock_nfs_file_handler, mock_db_session):
    request_data = BulkDownloadRequest(lan_ids=["LAN12345", "LAN67890"])
    user_id = "test_user"
    ip_address = "192.168.1.1"
    user_agent = "TestClient"

    # Mock the create_log call within record_bulk_download
    audit_log_service.create_log = AsyncMock(return_value=AuditLog(id=100, user_id=user_id, action="BULK_DOWNLOAD", resource_type="RECORDING_BATCH", timestamp=datetime.now(timezone.utc)))

    response = await audit_log_service.record_bulk_download(request_data, user_id, ip_address, user_agent)

    mock_nfs_file_handler.check_file_exists.assert_any_call("LAN12345")
    mock_nfs_file_handler.check_file_exists.assert_any_call("LAN67890")
    mock_nfs_file_handler.get_file_path.assert_any_call("LAN12345")
    mock_nfs_file_handler.get_file_path.assert_any_call("LAN67890")

    assert response["overall_status"] == "COMPLETED"
    assert len(response["results"]) == 2
    assert response["results"][0].status == "SUCCESS"
    assert response["results"][1].status == "SUCCESS"
    assert response["audit_log_id"] == 100
    audit_log_service.create_log.assert_called_once()
    assert audit_log_service.create_log.call_args[0][0].user_id == user_id
    assert audit_log_service.create_log.call_args[0][0].action == "BULK_DOWNLOAD"
    assert audit_log_service.create_log.call_args[0][0].details["successful_downloads"] == ["LAN12345", "LAN67890"]

@pytest.mark.asyncio
async def test_record_bulk_download_partial_success(audit_log_service, mock_nfs_file_handler, mock_db_session):
    request_data = BulkDownloadRequest(lan_ids=["LAN12345", "LAN_NOT_FOUND"])
    user_id = "test_user"

    audit_log_service.create_log = AsyncMock(return_value=AuditLog(id=101, user_id=user_id, action="BULK_DOWNLOAD", resource_type="RECORDING_BATCH", timestamp=datetime.now(timezone.utc)))

    response = await audit_log_service.record_bulk_download(request_data, user_id)

    assert response["overall_status"] == "PARTIAL_SUCCESS"
    assert len(response["results"]) == 2
    assert response["results"][0].status == "SUCCESS"
    assert response["results"][1].status == "NOT_FOUND"
    assert response["audit_log_id"] == 101
    assert audit_log_service.create_log.call_args[0][0].details["successful_downloads"] == ["LAN12345"]
    assert audit_log_service.create_log.call_args[0][0].details["failed_downloads"][0]["lan_id"] == "LAN_NOT_FOUND"

@pytest.mark.asyncio
async def test_record_bulk_download_all_failed(audit_log_service, mock_nfs_file_handler, mock_db_session):
    request_data = BulkDownloadRequest(lan_ids=["LAN_NOT_FOUND", "ANOTHER_NOT_FOUND"])
    user_id = "test_user"

    audit_log_service.create_log = AsyncMock(return_value=AuditLog(id=102, user_id=user_id, action="BULK_DOWNLOAD", resource_type="RECORDING_BATCH", timestamp=datetime.now(timezone.utc)))

    response = await audit_log_service.record_bulk_download(request_data, user_id)

    assert response["overall_status"] == "FAILED"
    assert len(response["results"]) == 2
    assert response["results"][0].status == "NOT_FOUND"
    assert response["results"][1].status == "NOT_FOUND"
    assert response["audit_log_id"] == 102
    assert audit_log_service.create_log.call_args[0][0].details["successful_downloads"] == []
    assert len(audit_log_service.create_log.call_args[0][0].details["failed_downloads"]) == 2

@pytest.mark.asyncio
async def test_record_bulk_download_empty_lan_ids(audit_log_service):
    request_data = BulkDownloadRequest(lan_ids=[])
    user_id = "test_user"

    with pytest.raises(InvalidInputException, match="No LAN IDs provided"):
        await audit_log_service.record_bulk_download(request_data, user_id)

@pytest.mark.asyncio
async def test_record_bulk_download_too_many_lan_ids(audit_log_service):
    request_data = BulkDownloadRequest(lan_ids=[f"LAN{i}" for i in range(12)]) # 12 IDs
    user_id = "test_user"

    with pytest.raises(InvalidInputException, match="Maximum 10 LAN IDs allowed"):
        await audit_log_service.record_bulk_download(request_data, user_id)

@pytest.mark.asyncio
async def test_record_bulk_download_nfs_error(audit_log_service, mock_nfs_file_handler, mock_db_session):
    request_data = BulkDownloadRequest(lan_ids=["LAN123"])
    user_id = "test_user"

    mock_nfs_file_handler.check_file_exists.side_effect = Exception("NFS connection lost")
    audit_log_service.create_log = AsyncMock(return_value=AuditLog(id=103, user_id=user_id, action="BULK_DOWNLOAD", resource_type="RECORDING_BATCH", timestamp=datetime.now(timezone.utc)))

    response = await audit_log_service.record_bulk_download(request_data, user_id)

    assert response["overall_status"] == "FAILED"
    assert len(response["results"]) == 1
    assert response["results"][0].status == "FAILED"
    assert "Internal error checking file" in response["results"][0].message
    assert response["audit_log_id"] == 103
    assert audit_log_service.create_log.call_args[0][0].details["successful_downloads"] == []
    assert audit_log_service.create_log.call_args[0][0].details["failed_downloads"][0]["lan_id"] == "LAN123"
    assert "NFS connection lost" in audit_log_service.create_log.call_args[0][0].details["failed_downloads"][0]["reason"]