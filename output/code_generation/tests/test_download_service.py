import pytest
from datetime import datetime
from uuid import uuid4
import os

from services.download_service import DownloadService
from crud import CRUDOperations
from models import DownloadRequest, FileMetadata, DownloadStatus, FileExistenceStatus
from schemas import BulkDownloadRequest, DownloadRequestCreate, DownloadRequestUpdate, FileMetadataSchema
from utils.exceptions import CustomValidationException, ServiceUnavailableException, NotFoundException

# Assuming conftest.py sets up db_session, crud_instance, download_service_instance fixtures

def test_process_bulk_download_request_success(db_session, crud_instance, download_service_instance):
    """Test successful processing of a bulk download request."""
    lan_ids = ["LAN1234567890", "LAN0987654321"] # These should exist as dummy files
    request_data = BulkDownloadRequest(lan_ids=lan_ids)
    requested_by = "test_user"

    response = download_service_instance.process_bulk_download_request(request_data, requested_by)

    assert response.status == DownloadStatus.COMPLETED
    assert response.total_files == 2
    assert response.files_found == 2
    assert response.files_not_found == 0
    assert response.files_error == 0
    assert len(response.files_details) == 2

    # Verify DB state
    db_request = crud_instance.get_download_request(response.request_id)
    assert db_request is not None
    assert db_request.status == DownloadStatus.COMPLETED
    assert db_request.total_files == 2
    assert db_request.files_found == 2

    for file_detail in response.files_details:
        assert file_detail.existence_status == FileExistenceStatus.EXISTS
        assert file_detail.file_path is not None
        assert file_detail.file_name is not None
        db_file_meta = crud_instance.get_file_metadata_by_lan_id(file_detail.lan_id)
        assert db_file_meta is not None
        assert db_file_meta.existence_status == FileExistenceStatus.EXISTS

def test_process_bulk_download_request_partial_success(db_session, crud_instance, download_service_instance):
    """Test processing with some files found and some not found."""
    lan_ids = ["LAN1234567890", "LAN_NOT_EXISTS"] # One exists, one doesn't
    request_data = BulkDownloadRequest(lan_ids=lan_ids)
    requested_by = "test_user"

    response = download_service_instance.process_bulk_download_request(request_data, requested_by)

    assert response.status == DownloadStatus.PARTIAL_SUCCESS
    assert response.total_files == 2
    assert response.files_found == 1
    assert response.files_not_found == 1
    assert response.files_error == 0
    assert len(response.files_details) == 2

    found_file = next(f for f in response.files_details if f.lan_id == "LAN1234567890")
    not_found_file = next(f for f in response.files_details if f.lan_id == "LAN_NOT_EXISTS")

    assert found_file.existence_status == FileExistenceStatus.EXISTS
    assert not_found_file.existence_status == FileExistenceStatus.NOT_FOUND
    assert not_found_file.error_message == "File not found on NFS."

def test_process_bulk_download_request_all_not_found(db_session, crud_instance, download_service_instance):
    """Test processing where all files are not found."""
    lan_ids = ["LAN_NOT_EXISTS_1", "LAN_NOT_EXISTS_2"]
    request_data = BulkDownloadRequest(lan_ids=lan_ids)
    requested_by = "test_user"

    response = download_service_instance.process_bulk_download_request(request_data, requested_by)

    assert response.status == DownloadStatus.FAILED
    assert response.total_files == 2
    assert response.files_found == 0
    assert response.files_not_found == 2
    assert response.files_error == 0
    assert len(response.files_details) == 2
    assert all(f.existence_status == FileExistenceStatus.NOT_FOUND for f in response.files_details)

def test_process_bulk_download_request_invalid_lan_id_format(db_session, crud_instance, download_service_instance):
    """Test processing with an invalid LAN ID format."""
    lan_ids = ["invalid-lan-id!", "LAN1234567890"]
    request_data = BulkDownloadRequest(lan_ids=lan_ids)
    requested_by = "test_user"

    response = download_service_instance.process_bulk_download_request(request_data, requested_by)

    assert response.status == DownloadStatus.PARTIAL_SUCCESS # Because one was valid
    assert response.total_files == 2
    assert response.files_found == 1
    assert response.files_not_found == 0
    assert response.files_error == 1
    assert len(response.files_details) == 2

    invalid_file = next(f for f in response.files_details if f.lan_id == "invalid-lan-id!")
    assert invalid_file.existence_status == FileExistenceStatus.ERROR
    assert invalid_file.error_message == "Invalid LAN ID format."

def test_process_bulk_download_request_empty_lan_ids(db_session, crud_instance, download_service_instance):
    """Test processing with an empty list of LAN IDs."""
    request_data = BulkDownloadRequest(lan_ids=[])
    requested_by = "test_user"

    with pytest.raises(CustomValidationException) as exc_info:
        download_service_instance.process_bulk_download_request(request_data, requested_by)
    assert "No LAN IDs provided" in str(exc_info.value.detail)

def test_process_bulk_download_request_too_many_lan_ids(db_session, crud_instance, download_service_instance):
    """Test processing with more than 10 LAN IDs."""
    lan_ids = [f"LAN{i:010d}" for i in range(11)] # 11 LAN IDs
    request_data = BulkDownloadRequest(lan_ids=lan_ids)
    requested_by = "test_user"

    with pytest.raises(CustomValidationException) as exc_info:
        download_service_instance.process_bulk_download_request(request_data, requested_by)
    assert "Maximum 10 LAN IDs allowed" in str(exc_info.value.detail)

def test_get_download_request_status_success(db_session, crud_instance, download_service_instance):
    """Test retrieving status of an existing request."""
    # First, create a request to retrieve
    lan_ids = ["LAN1234567890"]
    request_data = BulkDownloadRequest(lan_ids=lan_ids)
    requested_by = "test_user_status"
    created_response = download_service_instance.process_bulk_download_request(request_data, requested_by)
    
    # Now, retrieve it
    retrieved_response = download_service_instance.get_download_request_status(str(created_response.request_id))

    assert retrieved_response.request_id == created_response.request_id
    assert retrieved_response.status == created_response.status
    assert retrieved_response.total_files == created_response.total_files
    assert len(retrieved_response.files_details) == len(created_response.files_details)
    assert retrieved_response.files_details[0].lan_id == "LAN1234567890"

def test_get_download_request_status_not_found(db_session, crud_instance, download_service_instance):
    """Test retrieving status for a non-existent request."""
    non_existent_id = uuid4()
    with pytest.raises(NotFoundException) as exc_info:
        download_service_instance.get_download_request_status(str(non_existent_id))
    assert f"Download request with ID '{non_existent_id}' not found." in str(exc_info.value.detail)

def test_get_download_request_status_invalid_uuid(db_session, crud_instance, download_service_instance):
    """Test retrieving status with an invalid UUID format."""
    invalid_uuid = "not-a-uuid"
    with pytest.raises(CustomValidationException) as exc_info:
        download_service_instance.get_download_request_status(invalid_uuid)
    assert "Invalid request ID format" in str(exc_info.value.detail)

def test_nfs_path_not_accessible_error(db_session, crud_instance):
    """Test error handling when NFS_BASE_PATH is not accessible."""
    original_nfs_path = download_service_instance.nfs_base_path
    download_service_instance.nfs_base_path = "/non_existent_path_for_test" # Temporarily change to a bad path

    lan_ids = ["LAN1234567890"]
    request_data = BulkDownloadRequest(lan_ids=lan_ids)
    requested_by = "test_user"

    try:
        response = download_service_instance.process_bulk_download_request(request_data, requested_by)
        assert response.status == DownloadStatus.FAILED
        assert response.files_error == 1
        assert response.files_details[0].existence_status == FileExistenceStatus.ERROR
        assert "NFS base path not accessible." in response.files_details[0].error_message
    finally:
        download_service_instance.nfs_base_path = original_nfs_path # Restore original path