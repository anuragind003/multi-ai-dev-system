from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, status, UploadFile, File, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.core.dependencies import DBSession, CurrentUser, AdminUser
from app.services.vkyc_recording_service import VKYCRecordingService
from app.schemas.vkyc_recording import (
    VKYCRecordingCreate,
    VKYCRecordingUpdate,
    VKYCRecordingResponse,
    CSVUploadResult,
    VKYCRecordingListResponse
)
from app.schemas.auth import UserResponse # For type hinting current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vkyc-recordings", tags=["VKYC Recordings"])

@router.post(
    "/",
    response_model=VKYCRecordingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new VKYC recording metadata entry",
    description="Allows authenticated users (admin or regular) to create a single VKYC recording metadata entry."
)
async def create_vkyc_recording(
    recording_data: VKYCRecordingCreate,
    current_user: Annotated[CurrentUser, Depends()],
    db: Annotated[DBSession, Depends()]
):
    """
    Creates a new VKYC recording metadata entry.
    Requires authentication.
    """
    service = VKYCRecordingService(db)
    logger.info(f"User {current_user.username} attempting to create VKYC recording for LAN ID: {recording_data.lan_id}")
    new_record = service.create_recording(recording_data, current_user.username)
    return new_record

@router.post(
    "/upload-csv",
    response_model=CSVUploadResult,
    status_code=status.HTTP_200_OK,
    summary="Upload CSV file for bulk VKYC recording metadata ingestion",
    description="Allows admin users to upload a CSV file containing VKYC recording metadata for bulk ingestion. "
                "The system will create new records or update existing ones based on LAN ID."
)
async def upload_csv_for_ingestion(
    file: Annotated[UploadFile, File(description="CSV file containing VKYC recording metadata.")],
    current_user: Annotated[AdminUser, Depends()], # Only admin can upload CSV
    db: Annotated[DBSession, Depends()]
):
    """
    Uploads a CSV file for bulk ingestion of VKYC recording metadata.
    Requires admin authentication.
    """
    if not file.filename.lower().endswith('.csv'):
        logger.warning(f"User {current_user.username} attempted to upload non-CSV file: {file.filename}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Only CSV files are allowed."}
        )

    service = VKYCRecordingService(db)
    logger.info(f"User {current_user.username} attempting to upload CSV file: {file.filename}")
    
    try:
        csv_content = await file.read()
        result = service.ingest_csv_data(csv_content, current_user.username)
        logger.info(f"CSV upload for {file.filename} processed. Successful: {result.successful_ingestions}, Failed: {result.failed_ingestions}")
        return result
    except Exception as e:
        logger.error(f"Error processing CSV upload for {file.filename}: {e}", exc_info=True)
        # Specific exceptions from service layer are handled by global handlers
        # For generic errors, re-raise or return a generic error response
        raise

@router.get(
    "/{recording_id}",
    response_model=VKYCRecordingResponse,
    summary="Retrieve VKYC recording metadata by ID",
    description="Fetches a single VKYC recording metadata entry by its unique database ID."
)
async def get_vkyc_recording(
    recording_id: int,
    current_user: Annotated[CurrentUser, Depends()],
    db: Annotated[DBSession, Depends()]
):
    """
    Retrieves a VKYC recording by its ID.
    Requires authentication.
    """
    service = VKYCRecordingService(db)
    logger.info(f"User {current_user.username} requesting VKYC recording with ID: {recording_id}")
    record = service.get_recording_by_id(recording_id)
    return record

@router.get(
    "/",
    response_model=VKYCRecordingListResponse,
    summary="List VKYC recording metadata with filters and pagination",
    description="Retrieves a paginated list of VKYC recording metadata. "
                "Supports filtering by LAN ID, status, and recording date range."
)
async def list_vkyc_recordings(
    current_user: Annotated[CurrentUser, Depends()],
    db: Annotated[DBSession, Depends()],
    lan_id: Optional[str] = Query(None, description="Filter by LAN ID (partial match)."),
    status: Optional[str] = Query(None, description="Filter by recording status (e.g., PENDING, PROCESSED)."),
    start_date: Optional[datetime] = Query(None, description="Filter by recording date (start of range). Format: YYYY-MM-DDTHH:MM:SS"),
    end_date: Optional[datetime] = Query(None, description="Filter by recording date (end of range). Format: YYYY-MM-DDTHH:MM:SS"),
    skip: int = Query(0, ge=0, description="Number of records to skip (for pagination)."),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return (for pagination).")
):
    """
    Lists VKYC recording metadata with filtering and pagination.
    Requires authentication.
    """
    service = VKYCRecordingService(db)
    logger.info(f"User {current_user.username} requesting list of VKYC recordings with filters: LAN ID={lan_id}, Status={status}, Dates={start_date}-{end_date}, Skip={skip}, Limit={limit}")
    
    records, total_count = service.get_recordings(
        lan_id=lan_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )
    return VKYCRecordingListResponse(
        total=total_count,
        page=int(skip / limit) + 1,
        page_size=limit,
        items=records
    )

@router.put(
    "/{recording_id}",
    response_model=VKYCRecordingResponse,
    summary="Update an existing VKYC recording metadata entry",
    description="Updates an existing VKYC recording metadata entry by its unique database ID. "
                "Requires admin privileges."
)
async def update_vkyc_recording(
    recording_id: int,
    update_data: VKYCRecordingUpdate,
    current_user: Annotated[AdminUser, Depends()], # Only admin can update
    db: Annotated[DBSession, Depends()]
):
    """
    Updates an existing VKYC recording.
    Requires admin authentication.
    """
    service = VKYCRecordingService(db)
    logger.info(f"User {current_user.username} attempting to update VKYC recording with ID: {recording_id}")
    updated_record = service.update_recording(recording_id, update_data)
    return updated_record

@router.delete(
    "/{recording_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a VKYC recording metadata entry",
    description="Deletes a VKYC recording metadata entry by its unique database ID. "
                "Requires admin privileges."
)
async def delete_vkyc_recording(
    recording_id: int,
    current_user: Annotated[AdminUser, Depends()], # Only admin can delete
    db: Annotated[DBSession, Depends()]
):
    """
    Deletes a VKYC recording.
    Requires admin authentication.
    """
    service = VKYCRecordingService(db)
    logger.info(f"User {current_user.username} attempting to delete VKYC recording with ID: {recording_id}")
    service.delete_recording(recording_id)
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)