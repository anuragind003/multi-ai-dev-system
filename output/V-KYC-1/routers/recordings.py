import os
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import (
    RecordingMetadataCreate, RecordingMetadataUpdate, RecordingMetadataResponse,
    BulkUploadResult, ErrorResponse, RecordingFilter
)
from services import recording_service
from dependencies import get_db, get_auditor_or_admin_user, get_viewer_auditor_admin_user, get_admin_user
from utils.exceptions import NotFoundException, DuplicateEntryException, FileOperationException, BadRequestException
from utils.logger import logger
from models import UserRole, RecordingStatus, User

router = APIRouter()

@router.post(
    "/",
    response_model=RecordingMetadataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new recording metadata",
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Recording with this file path already exists"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient permissions"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def create_recording(
    recording_in: RecordingMetadataCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_auditor_or_admin_user) # Only auditors/admins can create
):
    """
    Creates new V-KYC recording metadata in the system.
    Requires 'auditor' or 'admin' role.
    """
    try:
        new_recording = await recording_service.create_recording_metadata(db, recording_in, current_user.id)
        return new_recording
    except DuplicateEntryException as e:
        logger.warning(f"Recording creation failed: {e.message}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred during recording creation: {e}")
        raise

@router.get(
    "/",
    response_model=List[RecordingMetadataResponse],
    summary="Get all recording metadata with filters",
    responses={
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient permissions"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_all_recordings(
    lan_id: Optional[str] = Query(None, description="Filter by Loan Account Number (partial match)"),
    customer_name: Optional[str] = Query(None, description="Filter by customer name (partial match)"),
    status: Optional[RecordingStatus] = Query(None, description="Filter by recording status"),
    start_date: Optional[datetime] = Query(None, description="Filter recordings from this date onwards (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter recordings up to this date (ISO 8601)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_viewer_auditor_admin_user) # Any authenticated user can view
):
    """
    Retrieves a list of V-KYC recording metadata.
    Supports filtering by LAN ID, customer name, status, and date range.
    Requires 'viewer', 'auditor', or 'admin' role.
    """
    try:
        recordings = await recording_service.get_all_recordings(
            db, skip, limit, lan_id, customer_name, status, start_date, end_date
        )
        return recordings
    except Exception as e:
        logger.exception(f"An unexpected error occurred while fetching recordings: {e}")
        raise

@router.get(
    "/{recording_id}",
    response_model=RecordingMetadataResponse,
    summary="Get recording metadata by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Recording not found"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient permissions"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_recording_by_id(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_viewer_auditor_admin_user) # Any authenticated user can view
):
    """
    Retrieves V-KYC recording metadata by its unique ID.
    Requires 'viewer', 'auditor', or 'admin' role.
    """
    try:
        recording = await recording_service.get_recording_metadata(db, recording_id)
        return recording
    except NotFoundException as e:
        logger.warning(f"Recording not found: {e.message}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred while fetching recording {recording_id}: {e}")
        raise

@router.put(
    "/{recording_id}",
    response_model=RecordingMetadataResponse,
    summary="Update recording metadata",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Recording not found"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient permissions"},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Update conflict (e.g., duplicate file path)"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_recording(
    recording_id: int,
    recording_update: RecordingMetadataUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_auditor_or_admin_user) # Only auditors/admins can update
):
    """
    Updates existing V-KYC recording metadata.
    Requires 'auditor' or 'admin' role.
    """
    try:
        updated_recording = await recording_service.update_recording_metadata(db, recording_id, recording_update, current_user.id)
        return updated_recording
    except NotFoundException as e:
        logger.warning(f"Recording update failed: {e.message}")
        raise e
    except DuplicateEntryException as e:
        logger.warning(f"Recording update failed due to conflict: {e.message}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred during recording update for ID {recording_id}: {e}")
        raise

@router.delete(
    "/{recording_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete recording metadata",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Recording not found"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient permissions"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user) # Only admins can delete
):
    """
    Deletes V-KYC recording metadata from the system.
    Requires 'admin' role.
    """
    try:
        await recording_service.delete_recording_metadata(db, recording_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundException as e:
        logger.warning(f"Recording deletion failed: {e.message}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred during recording deletion for ID {recording_id}: {e}")
        raise

@router.get(
    "/download/{recording_id}",
    summary="Download V-KYC recording file",
    responses={
        status.HTTP_200_OK: {"content": {"video/mp4": {}}, "description": "Recording file"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Recording metadata or file not found"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient permissions"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "File operation error"}
    }
)
async def download_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_viewer_auditor_admin_user) # Any authenticated user can download
):
    """
    Initiates download of a V-KYC recording file.
    Requires 'viewer', 'auditor', or 'admin' role.
    """
    try:
        recording = await recording_service.get_recording_metadata(db, recording_id)
        
        # In a real scenario, `recording.file_path` would be the actual path on the NFS server.
        # We would then stream this file. For demonstration, we'll use a dummy file.
        # Ensure the file path is safe and within allowed directories.
        
        # Simulate a file path on the local system for testing purposes
        # In production, this would be the NFS path, and you'd need to ensure
        # the FastAPI container has access to mount the NFS share.
        dummy_file_path = "dummy_recording.mp4"
        if not os.path.exists(dummy_file_path):
            # Create a dummy file if it doesn't exist for testing
            with open(dummy_file_path, "wb") as f:
                f.write(b"This is a dummy video file content.")
            logger.info(f"Created dummy file: {dummy_file_path}")

        # Use the actual file_path from the database in a real scenario
        # file_to_serve = recording.file_path
        file_to_serve = dummy_file_path # For demonstration

        if not os.path.exists(file_to_serve):
            raise FileOperationException(f"Recording file not found at {file_to_serve}.")

        # Determine media type (MIME type)
        # In a real app, you might infer this from the file extension or store it in DB
        media_type = "video/mp4" if file_to_serve.endswith(".mp4") else "application/octet-stream"

        logger.info(f"Serving file {file_to_serve} for recording ID {recording_id}.")
        return FileResponse(path=file_to_serve, media_type=media_type, filename=os.path.basename(file_to_serve))

    except NotFoundException as e:
        logger.warning(f"Download failed: {e.message}")
        raise e
    except FileOperationException as e:
        logger.error(f"File download error for recording ID {recording_id}: {e.message}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred during recording download for ID {recording_id}: {e}")
        raise

@router.post(
    "/bulk-upload",
    response_model=BulkUploadResult,
    summary="Bulk upload recording metadata from a file",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid file format or content"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient permissions"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def bulk_upload_recordings(
    file: UploadFile = File(..., description="CSV or Excel file containing recording metadata"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user) # Only admins can perform bulk uploads
):
    """
    Uploads a file (e.g., CSV) containing multiple V-KYC recording metadata entries for bulk processing.
    Requires 'admin' role.
    """
    if not file.filename.endswith(('.csv', '.xlsx')): # Basic file type check
        raise BadRequestException("Only CSV or XLSX files are allowed for bulk upload.")

    try:
        result = await recording_service.process_bulk_upload(db, file, current_user.id)
        return result
    except BadRequestException as e:
        logger.warning(f"Bulk upload failed: {e.message}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred during bulk upload: {e}")
        raise