from fastapi import APIRouter, Depends, status, UploadFile, File, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from models import (
    VKYCRecordCreate, VKYCRecordResponse, VKYCRecordUpdate,
    VKYCRecordFilter, BulkLANIDUpload, UserRole
)
from services.vkyc_service import VKYCService
from security import get_current_user, has_role
from database import get_db_session
from exceptions import NotFoundException, InvalidInputException, FileOperationError
from logger import get_logger
from config import get_settings

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter()

# Dependency to inject VKYCService
def get_vkyc_service(db: Session = Depends(get_db_session)) -> VKYCService:
    return VKYCService(db)

@router.post(
    "/records",
    response_model=VKYCRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new VKYC record",
    description="Allows an Admin or Team Lead to create a new VKYC record entry in the database."
)
async def create_vkyc_record(
    record: VKYCRecordCreate,
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: models.DBUser = Depends(has_role([UserRole.ADMIN, UserRole.TEAM_LEAD]))
):
    """
    Create a new VKYC record.
    - Requires `admin` or `team_lead` role.
    - Automatically sets `uploaded_by_user_id` to the current user's ID.
    """
    logger.info(f"User {current_user.username} attempting to create VKYC record for LAN ID: {record.lan_id}")
    db_record = vkyc_service.create_record(record, current_user.id)
    return VKYCRecordResponse.model_validate(db_record)

@router.get(
    "/records/{record_id}",
    response_model=VKYCRecordResponse,
    summary="Get a VKYC record by ID",
    description="Retrieves a single VKYC record by its unique ID. Accessible by all authenticated users."
)
async def get_vkyc_record(
    record_id: int,
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: models.DBUser = Depends(get_current_user) # Any authenticated user can view
):
    """
    Get a VKYC record by ID.
    - Requires authentication.
    """
    logger.info(f"User {current_user.username} attempting to retrieve VKYC record ID: {record_id}")
    db_record = vkyc_service.get_record_by_id(record_id)
    if not db_record:
        raise NotFoundException(detail=f"VKYC record with ID {record_id} not found.")
    return VKYCRecordResponse.model_validate(db_record)

@router.get(
    "/records",
    response_model=List[VKYCRecordResponse],
    summary="Search and filter VKYC records",
    description="Allows searching and filtering VKYC records based on various criteria like LAN ID, status, date range, and uploader. Supports pagination."
)
async def search_vkyc_records(
    filters: VKYCRecordFilter = Depends(), # Pydantic model for query parameters
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: models.DBUser = Depends(get_current_user) # Any authenticated user can search
):
    """
    Search and filter VKYC records.
    - Requires authentication.
    - Supports pagination (`limit`, `offset`).
    """
    logger.info(f"User {current_user.username} searching VKYC records with filters: {filters.model_dump_json()}")
    records = vkyc_service.get_records_by_filters(filters)
    return [VKYCRecordResponse.model_validate(record) for record in records]

@router.put(
    "/records/{record_id}",
    response_model=VKYCRecordResponse,
    summary="Update a VKYC record",
    description="Updates an existing VKYC record. Only Admin or Process Manager can update records."
)
async def update_vkyc_record(
    record_id: int,
    record_update: VKYCRecordUpdate,
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: models.DBUser = Depends(has_role([UserRole.ADMIN, UserRole.PROCESS_MANAGER]))
):
    """
    Update a VKYC record.
    - Requires `admin` or `process_manager` role.
    """
    logger.info(f"User {current_user.username} attempting to update VKYC record ID: {record_id}")
    db_record = vkyc_service.update_record(record_id, record_update)
    return VKYCRecordResponse.model_validate(db_record)

@router.delete(
    "/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a VKYC record",
    description="Deletes a VKYC record and its associated file. Only Admin can perform this action."
)
async def delete_vkyc_record(
    record_id: int,
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: models.DBUser = Depends(has_role([UserRole.ADMIN]))
):
    """
    Delete a VKYC record.
    - Requires `admin` role.
    - Deletes both the database entry and the file from NFS.
    """
    logger.info(f"User {current_user.username} attempting to delete VKYC record ID: {record_id}")
    vkyc_service.delete_record(record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post(
    "/records/bulk-upload-lan-ids",
    status_code=status.HTTP_200_OK,
    summary="Bulk upload LAN IDs",
    description="Allows Team Leads to upload a list of LAN IDs to create placeholder VKYC records. Max 10 LAN IDs per request."
)
async def bulk_upload_lan_ids(
    bulk_data: BulkLANIDUpload,
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: models.DBUser = Depends(has_role([UserRole.ADMIN, UserRole.TEAM_LEAD]))
):
    """
    Bulk upload LAN IDs.
    - Requires `admin` or `team_lead` role.
    - Processes a list of LAN IDs, creating placeholder records.
    - Returns a summary of successful and failed operations.
    """
    logger.info(f"User {current_user.username} initiating bulk upload for {len(bulk_data.lan_ids)} LAN IDs.")
    if len(bulk_data.lan_ids) > 10:
        raise InvalidInputException(detail="Maximum 10 LAN IDs allowed per bulk upload.")
    
    results = vkyc_service.process_bulk_lan_ids(bulk_data.lan_ids, current_user.id)
    return {"message": "Bulk processing complete", "results": results}

@router.post(
    "/records/{record_id}/upload-file",
    summary="Upload recording file for a VKYC record",
    description="Uploads the actual recording file to the NFS server for an existing VKYC record. Only Admin or Team Lead can upload files."
)
async def upload_vkyc_file(
    record_id: int,
    file: UploadFile = File(...),
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: models.DBUser = Depends(has_role([UserRole.ADMIN, UserRole.TEAM_LEAD]))
):
    """
    Upload a recording file for a VKYC record.
    - Requires `admin` or `team_lead` role.
    - The `record_id` must correspond to an existing VKYC record.
    - The file will be stored on the configured NFS mount point.
    """
    logger.info(f"User {current_user.username} attempting to upload file for record ID: {record_id}, filename: {file.filename}")
    db_record = vkyc_service.get_record_by_id(record_id)
    if not db_record:
        raise NotFoundException(detail=f"VKYC record with ID {record_id} not found.")

    try:
        # Use the LAN ID from the existing record for file naming consistency
        relative_file_path = vkyc_service.upload_recording_file(db_record.lan_id, file.file)
        
        # Update the record's file_path and status in the database
        update_data = VKYCRecordUpdate(file_path=relative_file_path, status=models.VKYCStatus.COMPLETED)
        updated_record = vkyc_service.update_record(record_id, update_data)
        
        logger.info(f"File '{file.filename}' uploaded and record ID {record_id} updated successfully.")
        return {"message": "File uploaded and record updated successfully", "record": VKYCRecordResponse.model_validate(updated_record)}
    except FileOperationError as e:
        logger.error(f"File upload failed for record ID {record_id}: {e.detail}", exc_info=True)
        raise e # Re-raise custom exception
    except Exception as e:
        logger.error(f"An unexpected error occurred during file upload for record ID {record_id}: {e}", exc_info=True)
        raise FileOperationError(detail=f"Failed to upload file: {e}")

@router.get(
    "/records/{record_id}/download-file",
    summary="Download recording file",
    description="Downloads the actual recording file associated with a VKYC record from the NFS server. Accessible by all authenticated users."
)
async def download_vkyc_file(
    record_id: int,
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: models.DBUser = Depends(get_current_user) # Any authenticated user can download
):
    """
    Download a recording file for a VKYC record.
    - Requires authentication.
    - Streams the file content from the NFS mount point.
    """
    logger.info(f"User {current_user.username} attempting to download file for record ID: {record_id}")
    try:
        full_file_path = vkyc_service.download_recording_file(record_id)
        
        def file_iterator():
            with open(full_file_path, mode="rb") as file_like:
                while chunk := file_like.read(settings.NFS_CHUNK_SIZE):
                    yield chunk

        file_name = full_file_path.split("/")[-1] # Extract filename from path
        logger.info(f"Streaming file '{file_name}' for record ID {record_id}.")
        return StreamingResponse(
            file_iterator(),
            media_type="application/octet-stream", # Or specific video type like "video/mp4"
            headers={"Content-Disposition": f"attachment; filename={file_name}"}
        )
    except NotFoundException as e:
        logger.warning(f"Download failed: {e.detail}")
        raise e
    except FileOperationError as e:
        logger.error(f"File download failed for record ID {record_id}: {e.detail}", exc_info=True)
        raise e
    except Exception as e:
        logger.error(f"An unexpected error occurred during file download for record ID {record_id}: {e}", exc_info=True)
        raise FileOperationError(detail=f"Failed to download file: {e}")